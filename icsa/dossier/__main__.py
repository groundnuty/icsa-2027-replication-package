"""python -m icsa.dossier CONFIG.json OUT.md  (CONFIG names every input explicitly; see README.md)"""
import pathlib
import sys

from .build import build

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    pathlib.Path(sys.argv[2]).write_text(build(sys.argv[1]))
