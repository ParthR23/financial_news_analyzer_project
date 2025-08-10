import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, FloatType
from sentence_transformers import SentenceTransformer
import json

from ..config import settings
from ..core.vector_db import VectorDB

# --- Setup basic logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_embedding(text: str) -> list[float]:
    """Generates a vector embedding for a given text."""
    # This function will be broadcast to each Spark executor.
    # We initialize the model inside the function to avoid serialization issues.
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embedding = model.encode(text)
    return embedding.tolist()

def run_embedding_job():
    """
    Main PySpark job to read raw data from S3, generate embeddings,
    and load them into a vector database.
    """
    logging.info("Starting PySpark embedding job...")

    spark = SparkSession.builder \
        .appName("FinancialNewsEmbedder") \
        .config("spark.hadoop.fs.s3a.access.key", settings.AWS_ACCESS_KEY_ID) \
        .config("spark.hadoop.fs.s3a.secret.key", settings.AWS_SECRET_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    logging.info("Spark session created.")

    # 1. Read raw JSON data from S3
    s3_path = f"s3a://{settings.S3_BUCKET_NAME}/raw_news/"
    raw_df = spark.read.json(s3_path)
    logging.info(f"Successfully read {raw_df.count()} articles from S3.")

    # 2. Define and apply the UDF to generate embeddings
    embedding_udf = udf(get_embedding, ArrayType(FloatType()))
    processed_df = raw_df.withColumn("embedding", embedding_udf(raw_df["content"]))
    
    # 3. Collect the processed data to the driver
    logging.info("Generating embeddings... This may take a while.")
    results = processed_df.select("title", "link", "published", "source", "content", "embedding").collect()
    logging.info(f"Successfully generated embeddings for {len(results)} articles.")

    # 4. Load data into the vector database
    vector_db = VectorDB()
    documents = []
    metadatas = []
    ids = []

    for row in results:
        documents.append(row['content'])
        metadatas.append({
            "title": row['title'],
            "link": row['link'],
            "published": row['published'],
            "source": row['source']
        })
        # Create a unique ID for each document
        ids.append(hashlib.md5(row['link'].encode()).hexdigest())

    if documents:
        vector_db.add_documents(documents=documents, metadatas=metadatas, ids=ids)
        logging.info(f"Successfully added {len(documents)} documents to the vector database.")
    else:
        logging.warning("No new documents to add to the vector database.")

    spark.stop()
    logging.info("PySpark job finished.")

if __name__ == "__main__":
    run_embedding_job()