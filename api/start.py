"""api/start.py -- Launch the PrivacyLens FastAPI server."""
import os
import sys
from pathlib import Path

# Ensure project root is always on sys.path so 'api', 'nlp', 'ingestion' are importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Also set PYTHONPATH so uvicorn's reload subprocess inherits it
os.environ["PYTHONPATH"] = str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "nlp", "ingestion", "audio"],
    )
