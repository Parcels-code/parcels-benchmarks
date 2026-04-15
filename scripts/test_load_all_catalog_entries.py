#!/usr/bin/env python3
"""Load and verify all catalog entries from both intake catalogs."""

import os
import sys
from pathlib import Path

# Ensure PIXI_PROJECT_ROOT is set so benchmarks/__init__.py can resolve relative paths
os.environ.setdefault("PIXI_PROJECT_ROOT", str(Path(__file__).parent))

from benchmarks.catalogs import Catalogs


def load_catalog(name: str, catalog) -> list[tuple[str, Exception]]:
    entries = list(catalog)
    print(f"\n=== {name} ({len(entries)} entries) ===")
    errors = []
    for entry_name in entries:
        try:
            ds = catalog[entry_name].to_dask()
            print(f"  OK  {entry_name}: {list(ds.data_vars)}")
        except Exception as exc:
            print(f"  ERR {entry_name}: {exc}")
            errors.append((entry_name, exc))
    return errors


def main() -> None:
    all_errors = []
    all_errors.extend(load_catalog("parcels-examples", Catalogs.CAT_EXAMPLES))
    all_errors.extend(load_catalog("parcels-benchmarks", Catalogs.CAT_BENCHMARKS))

    print(f"\n{'=' * 60}")
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s)")
        for name, exc in all_errors:
            print(f"  - {name}: {exc}")
        sys.exit(1)
    else:
        print("All catalog entries loaded successfully.")


if __name__ == "__main__":
    main()
