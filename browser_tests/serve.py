import tempfile
from pathlib import Path

import uvicorn

import db


def run():
    with tempfile.TemporaryDirectory(prefix="caresight-browser-") as directory:
        root = Path(directory)
        db.DB_FILE = str(root / "caresight.db")
        uvicorn.run("main:app", host="127.0.0.1", port=8767)


if __name__ == "__main__":
    run()
