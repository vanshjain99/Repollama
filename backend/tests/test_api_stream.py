from fastapi.testclient import TestClient
from repollama.main import app
import tempfile
from pathlib import Path

def test_analyze_stream_endpoint():
    client = TestClient(app)
    
    # Create a temporary directory structure to simulate a codebase
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create a sample python file
        py_file = tmp_path / "main.py"
        py_file.write_text("def hello():\n    print('Hello')\n")
        
        # Call the endpoint
        response = client.get(f"/api/v1/analyze/stream?path={tmp_path}")
        
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        # Read event data
        content = response.text
        assert "[System] Target workspace set to" in content
        assert "[AST] Parsing main.py..." in content
        assert "[System] Analysis complete." in content
        assert "[Pipeline] Analysis Complete!" in content

def test_analyze_stream_nonexistent_directory():
    client = TestClient(app)
    non_existent = "/non/existent/directory/path/here"
    
    response = client.get(f"/api/v1/analyze/stream?path={non_existent}")
    assert response.status_code == 200
    content = response.text
    assert "Error: Target workspace does not exist" in content
    assert "[Pipeline] Analysis Complete!" in content
