"""Wrapper around ChromaDB for storing and querying news article embeddings.

This module centralizes vector database interactions so other parts of the
application can remain agnostic of the underlying storage implementation.
"""
import chromadb
from sentence_transformers import SentenceTransformer
import logging
from ..config import settings

# --- Setup basic logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class VectorDB:
    """
    Handles all interactions with the ChromaDB vector store.
    """

    def __init__(self):
        # Initialize a persistent client. The data will be saved to disk.
        self.client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
        # Get or create the collection where news articles will be stored.
        self.collection = self.client.get_or_create_collection(name="financial_news")
        # Load the sentence transformer model for creating embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logging.info(f"VectorDB initialized. Collection 'financial_news' loaded/created.")

    def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """
        Adds a batch of documents and their metadata to the collection.
        """
        if not documents:
            logging.warning("add_documents called with no documents.")
            return

        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logging.info(f"Successfully added {len(documents)} documents to the collection.")
        except Exception as e:
            logging.error(f"Failed to add documents to ChromaDB: {e}")

    def query_documents(self, query_text: str, n_results: int = 3) -> list[dict]:
        """
        Takes a query text, embeds it, and returns the most similar documents.
        """
        try:
            # 1. Create an embedding for the input query text
            query_embedding = self.embedding_model.encode(query_text).tolist()

            # 2. Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            # 3. Format the results into a more usable structure
            formatted_results = []
            if results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i]
                    })

            logging.info(f"Query returned {len(formatted_results)} results.")
            return formatted_results

        except Exception as e:
            logging.error(f"Failed to query ChromaDB: {e}")
            return []