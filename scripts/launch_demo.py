#!/usr/bin/env python3
"""Launch local interactive demonstrator."""
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from vascushift.cli import cmd_demo
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    cmd_demo(args)

