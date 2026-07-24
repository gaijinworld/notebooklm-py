import json
import os
import urllib.request

url = "https://api.github.com/repos/gaijinworld/notebooklm-py/git/trees/main?recursive=1"
with urllib.request.urlopen(url, timeout=15) as resp:
    data = json.loads(resp.read().decode("utf-8"))

all_files = [i["path"] for i in data.get("tree", []) if i["type"] == "blob"]

skip_patterns = [
    ".venv",
    "node_modules",
    "__pycache__",
    ".git",
    "/dist/",
    ".map",
    ".pyc",
    "package-lock.json",
]


def should_skip(path):
    return any(p in path for p in skip_patterns)


diffs = []
checked = 0
for f in all_files:
    if should_skip(f):
        continue
    if not any(
        f.endswith(ext)
        for ext in [
            ".md",
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".json",
            ".toml",
            ".yml",
            ".yaml",
            ".sh",
            ".ps1",
            ".php",
            ".html",
            ".css",
            ".txt",
            ".cfg",
            ".ini",
            ".xml",
            ".svg",
        ]
    ):
        continue
    local_path = f"C:/src/notebooklm-py/{f}"
    if not os.path.exists(local_path):
        continue
    try:
        remote_url = f"https://raw.githubusercontent.com/gaijinworld/notebooklm-py/main/{f}"
        with urllib.request.urlopen(remote_url, timeout=10) as resp:
            remote = resp.read().decode("utf-8")
        with open(local_path, encoding="utf-8") as lf:
            local = lf.read()
        if local != remote:
            diffs.append(f)
            print(f"DIFF: {f} (local={len(local)} remote={len(remote)})")
        checked += 1
    except Exception:
        pass

print(f"\\nChecked: {checked}, Diffs: {len(diffs)}")
