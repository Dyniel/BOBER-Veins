#!/usr/bin/env python3
"""Run physiology Leave-One-Subject-Out experiment."""
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from vascushift.cli import cmd_train_physics
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(repo_root / "configs/physiology.yaml"))
    args = parser.parse_args()
    cmd_train_physics(args)

