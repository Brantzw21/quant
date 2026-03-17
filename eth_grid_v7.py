#!/usr/bin/env python3
"""Compatibility wrapper for the moved ETH project entrypoint."""

from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parent.parent / "eth" / "eth_grid_v7.py"
runpy.run_path(str(TARGET), run_name="__main__")
