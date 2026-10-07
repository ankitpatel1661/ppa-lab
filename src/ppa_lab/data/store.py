"""Raw-data cache: one Parquet file per dataset and month, plus a metadata sidecar.

Why bother?
- Reproducibility: every number in a report can be traced back to the exact
  file, request and download time it came from (the .meta.json "manifest").
- Politeness and speed: we download each month once, not on every run.
- Immutability: raw files are never edited. Corrections happen downstream, in
  the processed layer, so the original evidence is always available.

Layout:
    data/raw/energy_charts/<dataset>/<YYYY-MM>.parquet
    data/raw/energy_charts/<dataset>/<YYYY-MM>.meta.json
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ppa_lab.timeutils import normalise_index


@dataclass(frozen=True)
class RawStore:
    root: Path
    source: str = "energy_charts"

    def path(self, dataset: str, month: str) -> Path:
        return self.root / self.source / dataset / f"{month}.parquet"

    def meta_path(self, dataset: str, month: str) -> Path:
        return self.root / self.source / dataset / f"{month}.meta.json"

    def exists(self, dataset: str, month: str) -> bool:
        return self.path(dataset, month).exists() and self.meta_path(dataset, month).exists()

    def read_meta(self, dataset: str, month: str) -> dict[str, Any]:
        return json.loads(self.meta_path(dataset, month).read_text())

    def save(
        self,
        frame: pd.DataFrame,
        dataset: str,
        month: str,
        meta: dict[str, Any],
        overwrite: bool = False,
    ) -> Path:
        """Write a month atomically (temp file + rename) together with its manifest."""
        path = self.path(dataset, month)
        if path.exists() and not overwrite:
            raise FileExistsError(f"{path} exists; pass overwrite=True to replace it")
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_suffix(".parquet.tmp")
        frame.to_parquet(tmp)
        os.replace(tmp, path)  # atomic on the same filesystem: no half-written files

        manifest = {
            **meta,
            "dataset": dataset,
            "month": month,
            "rows": len(frame),
            "columns": list(frame.columns),
            "first_ts_utc": frame.index.min().isoformat() if len(frame) else None,
            "last_ts_utc": frame.index.max().isoformat() if len(frame) else None,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "written_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        self.meta_path(dataset, month).write_text(json.dumps(manifest, indent=2, default=str))
        return path

    def months(self, dataset: str) -> list[str]:
        folder = self.root / self.source / dataset
        return sorted(p.stem for p in folder.glob("*.parquet")) if folder.exists() else []

    def load(self, dataset: str, months: list[str] | None = None) -> pd.DataFrame:
        """Concatenate cached months (all of them by default), sorted by time."""
        months = months if months is not None else self.months(dataset)
        if not months:
            raise FileNotFoundError(
                f"No cached '{dataset}' data under {self.root / self.source}. Run `ppa-lab fetch`."
            )
        frames = [pd.read_parquet(self.path(dataset, m)) for m in months]
        combined = pd.concat(frames).sort_index()
        combined.index = normalise_index(combined.index)
        return combined
