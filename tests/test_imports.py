import os
import subprocess
import sys
from pathlib import Path


def test_all_modules_import_without_work(tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = """
import concurrent.futures
import importlib
import pathlib
import signal
import sqlite3
import sys
from unittest.mock import patch
import requests
import spacy

sys.dont_write_bytecode = True
def forbidden(*args, **kwargs):
    raise AssertionError("Import hat Arbeit ausgelöst")
def audit(event, args):
    if event.startswith("socket."):
        forbidden()
    if event == "open" and isinstance(args[0], str):
        if not args[0].endswith((".py", ".pyc")):
            raise AssertionError("Dateizugriff beim Import: " + args[0])
sys.addaudithook(audit)
with patch.object(spacy, "load", forbidden), \\
     patch.object(requests, "get", forbidden), \\
     patch.object(sqlite3, "connect", forbidden), \\
     patch.object(signal, "signal", forbidden), \\
     patch.object(concurrent.futures.ThreadPoolExecutor, "__init__", forbidden), \\
     patch.object(concurrent.futures.ProcessPoolExecutor, "__init__", forbidden):
    for name in sys.argv[1:]:
        importlib.import_module(name)
"""
    modules = [
        f"data_extraction.{path.stem}"
        for path in (root / "data_extraction").glob("*.py")
    ]
    result = subprocess.run(
        [sys.executable, "-c", code, *modules],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert list(tmp_path.iterdir()) == []
