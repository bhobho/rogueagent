# world.py
# The agent's pretend computer.
#
# Every run starts by copying the files in world_files/ into a plain Python
# dict: {"config/tools.json": "...file text...", ...}. The agent's tools read
# and write ONLY this dict. Nothing the agent does ever changes a real file on
# disk, so every run starts from the same clean state and your computer is safe.

import os

WORLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_files")


def load_world():
    """Read every file under world_files/ into a dict of path -> text."""
    files = {}
    for folder, subfolders, names in os.walk(WORLD_DIR):
        for name in names:
            full_path = os.path.join(folder, name)
            # Store paths the way the agent will see them: "config/tools.json"
            relative = os.path.relpath(full_path, WORLD_DIR).replace(os.sep, "/")
            with open(full_path, encoding="utf-8") as f:
                files[relative] = f.read()
    return files


def normalize_path(path):
    """Make "/config/tools.json", "./config/tools.json" and "config/tools.json"
    all mean the same file. Small models are not consistent about this, and we
    don't want a run to fail just because of a leading slash."""
    path = str(path or "").strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    path = path.strip("/")
    if path == ".":
        path = ""
    return path


def list_files(files, path):
    folder = normalize_path(path)
    prefix = folder + "/" if folder else ""
    matches = sorted(p for p in files if p.startswith(prefix))
    if not matches:
        return "No files found under '" + (folder or ".") + "'."
    return "\n".join(matches)


def read_file(files, path):
    path = normalize_path(path)
    if path not in files:
        return "ERROR: file not found: " + path
    return files[path]


def write_file(files, path, content):
    path = normalize_path(path)
    files[path] = str(content)
    return "OK: wrote " + str(len(files[path])) + " characters to " + path
