import os
import sys
import uvicorn

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from repollama.main import app
from repollama.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )
