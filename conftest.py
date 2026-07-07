"""Pytest configuration.

Force the Monte-Carlo simulation onto the single-process path during tests so the suite
stays fast and deterministic (the process pool is exercised in production, not in unit
tests). Set before any test imports ``simulation``.
"""
import os

os.environ.setdefault("SIM_WORKERS", "1")
