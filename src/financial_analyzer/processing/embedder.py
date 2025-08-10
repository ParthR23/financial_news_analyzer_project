import logging
import boto3
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, lit
from pyspark.sql.types import ArrayType, FloatType
from sentence_transformers import SentenceTransformer
import hashlib
import tempfile
import os

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_embedding(text: str) -> list[float]:
    """Generates a vector embedding for a given text."""
    # Initialize the model inside the function to avoid serialization issues
    if not hasattr(get_embedding, 'model'):
        get_embedding.model = SentenceTransformer('all-MiniLM-L6-v2')

    embedding = get_embedding.model.encode(text)
    return embedding.tolist()


def download_s3_data_locally(bucket_name, prefix, aws_access_key, aws_secret_key):
    """Download S3 data to local temporary directory to bypass S3A issues."""
    logging.info("Downloading S3 data to local directory to bypass S3A issues...")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )

    try:
        # List all objects with the given prefix
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        if 'Contents' not in response:
            logging.warning(f"No files found in s3://{bucket_name}/{prefix}")
            return temp_dir

        downloaded_files = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.json'):
                local_path = os.path.join(temp_dir, os.path.basename(key))
                s3_client.download_file(bucket_name, key, local_path)
                downloaded_files.append(local_path)
                logging.info(f"Downloaded {key} to {local_path}")

        logging.info(f"Downloaded {len(downloaded_files)} JSON files to {temp_dir}")
        return temp_dir

    except Exception as e:
        logging.error(f"Error downloading from S3: {e}")
        raise


def run_embedding_job():
    """
    Main PySpark job to read raw data, generate embeddings,
    and load them into a vector database - bypassing S3A issues.
    """
    logging.info("Starting PySpark embedding job...")

    # Import settings here to avoid circular imports
    try:
        if __name__ == "__main__" and __package__ is None:
            # Add src to path to allow absolute imports
            import sys
            from pathlib import Path
            file = Path(__file__).resolve()
            parent, root = file.parent, file.parents[2]
            sys.path.append(str(root))
            from src.financial_analyzer.config import settings
            from src.financial_analyzer.core.vector_db import VectorDB
        else:
            from ..config import settings
            from ..core.vector_db import VectorDB
    except ImportError as e:
        logging.error(f"Import error: {e}")
        raise

    # Create minimal Spark session without S3 dependencies
    spark = SparkSession.builder \
        .appName("FinancialNewsEmbedder") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

    logging.info("Spark session created.")

    temp_dir = None
    try:
        # Download S3 data locally to bypass S3A configuration issues
        temp_dir = download_s3_data_locally(
            bucket_name=settings.S3_BUCKET_NAME,
            prefix="raw_news/",
            aws_access_key=settings.AWS_ACCESS_KEY_ID,
            aws_secret_key=settings.AWS_SECRET_ACCESS_KEY
        )

        # Read JSON files from local directory
        json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
        if not json_files:
            logging.warning("No JSON files found in downloaded data")
            return

        local_path = os.path.join(temp_dir, "*.json")
        raw_df = spark.read.json(local_path)
        logging.info(f"Successfully read {raw_df.count()} articles from local files.")

        # Define and apply the UDF to generate embeddings
        embedding_udf = udf(get_embedding, ArrayType(FloatType()))
        processed_df = raw_df.withColumn("embedding", embedding_udf(raw_df["content"]))

        # Collect the processed data to the driver
        logging.info("Generating embeddings... This may take a while.")
        results = processed_df.select("title", "link", "published", "source", "content", "embedding").collect()
        logging.info(f"Successfully generated embeddings for {len(results)} articles.")

        # Load data into the vector database
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

    except Exception as e:
        logging.error(f"Error in embedding job: {e}")
        raise

    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            logging.info("Cleaned up temporary files.")

        spark.stop()
        logging.info("PySpark job finished.")


if __name__ == "__main__":
    run_embedding_job()