from fastapi.testclient import TestClient
from repollama.main import app, ollama_manager
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

def test_get_settings():
    client = TestClient(app)
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "ollama_base_url" in data
    assert "default_model" in data

def test_update_settings():
    client = TestClient(app)
    original_url = ollama_manager.base_url
    try:
        response = client.post("/api/v1/settings", json={"ollama_base_url": "http://mock-ollama:11434/"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["settings"]["ollama_base_url"] == "http://mock-ollama:11434"
        assert ollama_manager.base_url == "http://mock-ollama:11434"
    finally:
        # Reset settings
        ollama_manager.base_url = original_url

def test_get_graph_nonexistent():
    client = TestClient(app)
    # Patch Path to simulate file not existing
    with patch("repollama.main.Path.exists", return_value=False):
        response = client.get("/api/v1/graph")
        assert response.status_code == 200
        assert response.json() == {"nodes": [], "links": [], "error": "Graph data not found. Run analysis first."}

def test_get_graph_exists():
    client = TestClient(app)
    mock_data = {"nodes": [{"id": "foo"}], "links": []}
    
    with patch("repollama.main.Path.exists", return_value=True):
        with patch("builtins.open", mock_open := MagicMock()):
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mock_data)
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Patch json.load to return mock_data directly to bypass file reads
            with patch("json.load", return_value=mock_data):
                response = client.get("/api/v1/graph")
                assert response.status_code == 200
                assert response.json() == {**mock_data, "source_path": ".repollama_data/graph.json"}

@patch("repollama.main.LocalVectorStore")
@patch("repollama.main.ollama_manager.generate", new_callable=AsyncMock)
def test_chat_rag(mock_generate, mock_vector_store):
    client = TestClient(app)
    
    # Mock Vector Store results
    mock_vs_instance = MagicMock()
    mock_vs_instance.query_similar.return_value = [
        {"id": "file.py", "document": "def hello(): pass", "metadata": {"file_path": "file.py", "language": "python"}}
    ]
    mock_vector_store.return_value = mock_vs_instance
    
    # Mock Ollama generation response
    mock_generate.return_value = "This is a mock response from Ollama."
    
    response = client.post("/api/v1/chat", json={"message": "how does this work?", "model": "test-model"})
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "This is a mock response from Ollama."
    
    # Verify vector store query was called
    mock_vs_instance.query_similar.assert_called_once_with("how does this work?", n_results=5, repo_path="")
    
    # Verify LLM generation was called with prompt and model
    mock_generate.assert_called_once()
    args, kwargs = mock_generate.call_args
    assert "how does this work?" in args[0]
    assert "def hello(): pass" in args[0]
    assert args[1] == "test-model"
