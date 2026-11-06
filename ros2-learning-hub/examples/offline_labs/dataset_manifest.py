"""Create a deterministic manifest on stdout. Input data is never modified."""
import hashlib
import json
import sys
from pathlib import Path

def manifest(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("dataset root must be a directory")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symbolic links require an explicit data policy")
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        files.append({"path": path.relative_to(root).as_posix(),
                      "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    return {"schema": 1, "files": files}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 dataset_manifest.py DATA_DIRECTORY")
    print(json.dumps(manifest(sys.argv[1]), ensure_ascii=False, indent=2))
