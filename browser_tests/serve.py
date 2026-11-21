import tempfile
from pathlib import Path

import uvicorn

import escalations
import observations
import patients


def run():
    with tempfile.TemporaryDirectory(prefix="caresight-browser-") as directory:
        root = Path(directory)
        escalations.ESCALATIONS_FILE = str(root / "escalations.json")
        observations.OBSERVATIONS_FILE = str(root / "observations.json")
        patients.PATIENTS_FILE = str(root / "patients.json")
        uvicorn.run("main:app", host="127.0.0.1", port=8767)


if __name__ == "__main__":
    run()
