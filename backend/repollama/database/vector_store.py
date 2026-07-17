from __future__ import annotations
from typing import Any
import chromadb


class LocalVectorStore:
    """A persistent local vector database interface using ChromaDB.

    Stores code embeddings and metadata in a persistent local directory.
    """

    def __init__(self) -> None:
        """Initialize a persistent ChromaDB client and get or create the collection."""
        # Store the database locally in .repollama_data/chroma in current working directory
        self.client = chromadb.PersistentClient(path=".repollama_data/chroma")
        self.collection = self.client.get_or_create_collection(name="repo_code_index")

    def add_document(self, doc_id: str, text: str, metadata: dict[str, Any]) -> None:
        """Add a document (code snippet or file summary) to the vector store.

        Args:
            doc_id: Unique identifier for the document.
            text: The text content of the document.
            metadata: Key-value metadata associated with the document.
        """
        self.collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata]
        )

    def query_similar(self, query_text: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Query the collection for the most similar documents.

        Args:
            query_text: The semantic query string.
            n_results: Maximum number of results to return.

        Returns:
            A list of dicts, each with 'id', 'document', 'metadata', and 'distance'.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        formatted_results = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            ids = results["ids"][0]
            # Ensure safe indexing in case metadatas or distances are missing or smaller
            metadatas = (
                results["metadatas"][0]
                if "metadatas" in results and results["metadatas"]
                else [None] * len(docs)
            )
            distances = (
                results["distances"][0]
                if "distances" in results and results["distances"]
                else [None] * len(docs)
            )
            for doc, doc_id, meta, dist in zip(docs, ids, metadatas, distances):
                formatted_results.append({
                    "id": doc_id,
                    "document": doc,
                    "metadata": meta,
                    "distance": dist
                })
        return formatted_results
