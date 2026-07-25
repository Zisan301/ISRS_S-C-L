from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
manifest_path = ROOT / "MANIFEST.json"

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None

files = []
for path in sorted(ROOT.rglob("*")):
    if path.is_file() and path.name != "MANIFEST.json":
        files.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

manifest = {
    "release": "pnc-v1.0",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "git_commit_sha": run_cmd(["git", "rev-parse", "HEAD"]),
    "git_branch": run_cmd(["git", "branch", "--show-current"]),
    "python_version": sys.version,
    "platform": platform.platform(),
    "pip_freeze": run_cmd([sys.executable, "-m", "pip", "freeze"]),
    "files": files,
}

manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Wrote {manifest_path}")
print(f"Files recorded: {len(files)}")
print(f"Git SHA: {manifest['git_commit_sha']}")
