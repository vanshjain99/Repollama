from __future__ import annotations
from typing import Any
import hashlib
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

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any],
        repo_path: str = "",
    ) -> None:
        """Add a document (code snippet or file summary) to the vector store.

        Args:
            doc_id: Unique identifier for the document (usually the relative file path).
            text: The text content of the document.
            metadata: Key-value metadata associated with the document.
            repo_path: Absolute path of the repository this document belongs to.
                       Stored in metadata so queries can be scoped per-repo.
                       Also used to namespace the doc_id to prevent cross-repo
                       collisions when the same relative file path appears in
                       multiple repositories.
        """
        if repo_path:
            metadata = {**metadata, "repo_path": repo_path}
            # Namespace the ID so identical relative paths from different repos
            # don't overwrite each other in ChromaDB's collection.
            repo_hash = hashlib.md5(repo_path.encode()).hexdigest()[:8]
            unique_id = f"{repo_hash}::{doc_id}"
        else:
            unique_id = doc_id

        # ChromaDB upsert avoids duplicate-key errors on re-index runs.
        self.collection.upsert(
            ids=[unique_id],
            documents=[text],
            metadatas=[metadata]
        )

    def query_similar(
        self,
        query_text: str,
        n_results: int = 5,
        repo_path: str = "",
    ) -> list[dict[str, Any]]:
        """Query the collection for the most similar documents.

        Args:
            query_text: The semantic query string.
            n_results: Maximum number of results to return.
            repo_path: When provided, restricts results to documents that were
                       indexed from this specific repository path (via ChromaDB
                       ``where`` metadata filter).  Pass an empty string to
                       search across all repositories.

        Returns:
            A list of dicts, each with 'id', 'document', 'metadata', and 'distance'.
        """
        query_kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if repo_path and repo_path.strip():
            query_kwargs["where"] = {"repo_path": repo_path.strip()}

        try:
            results = self.collection.query(**query_kwargs)
        except Exception as exc:
            # ChromaDB raises when n_results > number of documents in the
            # filtered subset (or the collection is empty).  Retry once with a
            # smaller n_results derived from the actual collection count, then
            # give up gracefully.
            try:
                total = self.collection.count()
                if total == 0:
                    return []
                fallback_n = max(1, min(n_results, total))
                query_kwargs["n_results"] = fallback_n
                results = self.collection.query(**query_kwargs)
            except Exception:
                # If the second attempt also fails (e.g. where filter matches
                # zero docs), return an empty list so the chat endpoint can
                # still respond with general LLM knowledge.
                return []

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
