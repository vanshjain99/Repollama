from unittest.mock import MagicMock, patch
from repollama.database.vector_store import LocalVectorStore


@patch("chromadb.PersistentClient")
def test_vector_store_initialization(mock_client):
    mock_collection = MagicMock()
    mock_client.return_value.get_or_create_collection.return_value = mock_collection

    store = LocalVectorStore()

    mock_client.assert_called_once_with(path=".repollama_data/chroma")
    mock_client.return_value.get_or_create_collection.assert_called_once_with(
        name="repo_code_index"
    )
    assert store.collection == mock_collection


@patch("chromadb.PersistentClient")
def test_add_document(mock_client):
    mock_collection = MagicMock()
    mock_client.return_value.get_or_create_collection.return_value = mock_collection

    store = LocalVectorStore()
    store.add_document("doc_1", "print('hello')", {"language": "python"})

    mock_collection.upsert.assert_called_once_with(
        ids=["doc_1"],
        documents=["print('hello')"],
        metadatas=[{"language": "python"}],
    )


@patch("chromadb.PersistentClient")
def test_query_similar(mock_client):
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "ids": [["doc_1", "doc_2"]],
        "documents": [["doc1 content", "doc2 content"]],
        "metadatas": [[{"lang": "py"}, {"lang": "js"}]],
        "distances": [[0.1, 0.4]],
    }
    mock_client.return_value.get_or_create_collection.return_value = mock_collection

    store = LocalVectorStore()
    results = store.query_similar("hello", n_results=2)

    mock_collection.query.assert_called_once_with(
        query_texts=["hello"], n_results=2
    )

    assert len(results) == 2
    assert results[0]["id"] == "doc_1"
    assert results[0]["document"] == "doc1 content"
    assert results[0]["metadata"] == {"lang": "py"}
    assert results[0]["distance"] == 0.1

    assert results[1]["id"] == "doc_2"
    assert results[1]["document"] == "doc2 content"
    assert results[1]["metadata"] == {"lang": "js"}
    assert results[1]["distance"] == 0.4
