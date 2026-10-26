#!/usr/bin/env python3
"""Run data audit for ESA Headward Fluid Shift dataset."""
import sys
from pathlib import Path

# Add src to pythonpath
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from vascushift.cli import cmd_data_audit
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(repo_root / "configs/data.yaml"))
    args = parser.parse_args()
    cmd_data_audit(args)

