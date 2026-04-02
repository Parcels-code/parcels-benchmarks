#!/usr/bin/env python3
"""Download and extract a catalog zip archive, unzipping all zip archives contained within."""

import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path

from benchmarks import PARCELS_BENCHMARKS_DATA_FOLDER


def extract_zip_url(catalog_path: Path) -> str:
    with catalog_path.open() as f:
        first_line = f.readline().strip()
    if not first_line.startswith("# zip_url:"):
        raise ValueError(f"First line must be '# zip_url: <url>', got: {first_line!r}")
    url = first_line.removeprefix("# zip_url:").strip()
    if not url:
        raise ValueError("zip_url is empty")
    return url


def download_file(url: str, dest_dir: Path) -> Path:
    dest = dest_dir / "data.zip"
    print(f"Downloading {url} -> {dest}")
    subprocess.run(["curl", "-L", "-o", str(dest), url], check=True)
    return dest


def unzip_recursive(directory: Path) -> None:
    """Recursively find and extract all zip files, deleting originals."""
    found = list(directory.rglob("*.zip"))
    if not found:
        return
    for zip_path in found:
        print(f"Extracting {zip_path}")
        extract_to = zip_path.parent / zip_path.stem
        extract_to.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_to)
        zip_path.unlink()
        print(f"Deleted {zip_path}")
        # Collapse data/data -> data if the only child is a same-named folder
        sole_child = extract_to / zip_path.stem
        if sole_child.is_dir() and len(list(extract_to.iterdir())) == 1:
            for item in sole_child.iterdir():
                item.rename(extract_to / item.name)
            sole_child.rmdir()
    # recurse in case extracted zips contained more zips
    unzip_recursive(directory)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and extract a catalog archive."
    )
    parser.add_argument("catalog", type=Path, help="Path to catalog.yml")
    parser.add_argument(
        "output_dir",
        type=str,
        help="Subdirectory in PARCELS_BENCHMARKS_DATA_FOLDER to extract into",
    )
    args = parser.parse_args()
    output_dir = PARCELS_BENCHMARKS_DATA_FOLDER / args.output_dir
    catalog_path = output_dir / args.catalog.name

    if not args.catalog.is_file():
        raise SystemExit(f"catalog file not found: {args.catalog}")
    if output_dir.exists():
        shutil.copy(args.catalog, catalog_path)
        print(f"Copied catalogue across to {catalog_path}")
        print("Output directory already exists! Exiting...")
        return

    output_dir.mkdir(parents=True)
    shutil.copy(args.catalog, catalog_path)
    print(f"Copied catalogue across to {catalog_path}")

    url = extract_zip_url(args.catalog)
    download_file(url, output_dir)
    unzip_recursive(output_dir)

    print("Done.")


if __name__ == "__main__":
    main()
