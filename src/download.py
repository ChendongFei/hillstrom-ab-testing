"""Download the Kaggle mirror and verify its exact CSV bytes."""
from pathlib import Path
from urllib.request import urlopen
import io, zipfile, hashlib
from src.analysis import SHA, ROOT
URL='https://www.kaggle.com/api/v1/datasets/download/bofulee/kevin-hillstrom-minethatdata-e-mailanalytics'
def main():
    with urlopen(URL,timeout=120) as response:
        z=zipfile.ZipFile(io.BytesIO(response.read()))
    names=[n for n in z.namelist() if n.endswith('.csv')]
    if len(names)!=1: raise ValueError('Unexpected archive contents')
    content=z.read(names[0])
    if hashlib.sha256(content).hexdigest()!=SHA: raise ValueError('Dataset changed: audit before accepting')
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data/hillstrom.csv').write_bytes(content)
if __name__=='__main__': main()
