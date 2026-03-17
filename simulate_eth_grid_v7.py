#!/usr/bin/env python3
"""Compatibility wrapper for the moved ETH simulator entrypoint."""

from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parent.parent / "eth" / "simulate_eth_grid_v7.py"
runpy.run_path(str(TARGET), run_name="__main__")
