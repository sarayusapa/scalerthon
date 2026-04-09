"""
Server entry point for openenv-core multi-mode deployment.
Delegates to the main FastAPI app.
"""
import sys
import os

# Ensure project root is on the path so main.py / environment.py etc. are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: F401  re-exported for openenv-core


def main() -> None:
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
