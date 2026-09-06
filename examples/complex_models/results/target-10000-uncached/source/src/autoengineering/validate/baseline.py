"""Baseline data loading and storage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_baseline(path: str | Path) -> pd.DataFrame | np.ndarray:
    """Load baseline data from a file.

    Supports CSV and numpy (.npy) formats.
    """
    path = Path(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    elif path.suffix == ".npy":
        return np.load(path)
    else:
        raise ValueError(f"Unsupported baseline format: {path.suffix} (use .csv or .npy)")


def save_baseline(data: pd.DataFrame | np.ndarray, path: str | Path):
    """Save baseline data to a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, pd.DataFrame):
        data.to_csv(path, index=False)
    elif isinstance(data, np.ndarray):
        np.save(path, data)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")
