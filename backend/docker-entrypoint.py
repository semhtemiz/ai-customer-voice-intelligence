"""Idempotent import on startup, followed by the persistent API process."""
import os
import subprocess
import sys
from pathlib import Path

dataset=Path('/app/dataset/Womens Clothing E-Commerce Reviews.csv')
if not dataset.is_file():
    print('Missing dataset CSV. Mount dataset/ and place the original CSV there.',file=sys.stderr)
    sys.exit(1)
# Importer leaves compatible, same-checksum analysis runs untouched.
subprocess.run([sys.executable,'-m','backend.scripts.import_reviews','--input',str(dataset)],check=True)
os.execv(sys.executable,[sys.executable,'-m','uvicorn','backend.app.main:app','--host','0.0.0.0','--port','8000'])
