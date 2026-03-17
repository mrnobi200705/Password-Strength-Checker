#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
MANIFEST_PATH = BASE_DIR / "password_tool.manifest.json"
FILES = [
    "password_tool.py",
    "benchmark_password_tool.py",
]

manifest = {"version": 1, "files": {}}
for rel in FILES:
    file_path = BASE_DIR / rel
    manifest["files"][rel] = hashlib.sha256(file_path.read_bytes()).hexdigest()

MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
print(f"Updated {MANIFEST_PATH}")
