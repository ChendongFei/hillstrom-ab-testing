"""Download the dataset from its Kaggle mirror and verify its contents.

The mirror serves a zip with a single CSV. The file is only written to
data/hillstrom.csv if its SHA-256 matches the hash the analysis expects.
If the source file ever changes, this stops instead of letting
different data into the analysis unnoticed.

No Kaggle account or API key is needed for this public download.
Run from the repository root:  python -m src.download
"""

import hashlib
import io
import zipfile
from urllib.request import urlopen

from src.analysis import EXPECTED_SHA256, ROOT

URL = "https://www.kaggle.com/api/v1/datasets/download/bofulee/kevin-hillstrom-minethatdata-e-mailanalytics"


def main():
    with urlopen(URL, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    names = [n for n in archive.namelist() if n.endswith(".csv")]
    if len(names) != 1:
        raise ValueError("Unexpected archive contents")
    content = archive.read(names[0])
    if hashlib.sha256(content).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Dataset changed: audit before accepting")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "hillstrom.csv").write_bytes(content)


if __name__ == "__main__":
    main()
