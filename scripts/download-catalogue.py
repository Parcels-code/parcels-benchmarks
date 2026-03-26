#!/usr/bin/env python3
"""Download and extract a catalogue zip archive."""

import argparse
import shutil
import zipfile
from pathlib import Path

import subprocess
import os

try:
    PARCELS_BENCHMARKS_DATA_FOLDER = Path(os.environ["PARCELS_BENCHMARKS_DATA_FOLDER"])
except KeyError as e:
    raise RuntimeError("Set the PARCELS_BENCHMARKS_DATA_FOLDER environment variable to specify where the data should be downloaded.") from e

def extract_zip_url(catalogue_path: Path) -> str:
    with catalogue_path.open() as f:
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
    print(f"found={found}")
    for zip_path in found:
        print(f"Extracting {zip_path}")
        extract_to = zip_path.parent
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_to)
        zip_path.unlink()
        print(f"Deleted {zip_path}")
    # recurse in case extracted zips contained more zips
    unzip_recursive(directory)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and extract a catalogue archive."
    )
    parser.add_argument("catalogue", type=Path, help="Path to catalogue.yml")
    parser.add_argument("output_dir", type=str, help="Subdirectory in PARCELS_BENCHMARKS_DATA_FOLDER to extract into")
    args = parser.parse_args()
    output_dir = PARCELS_BENCHMARKS_DATA_FOLDER / args.output_dir
    if output_dir.exists():
        print("Output directory already exists! Exiting...")
        return

    if not args.catalogue.is_file():
        raise SystemExit(f"catalogue file not found: {args.catalogue}")

    output_dir.mkdir(parents=True, exist_ok=True)

    url = extract_zip_url(args.catalogue)
    download_file(url, output_dir)
    unzip_recursive(output_dir)

    shutil.copy(args.catalogue, output_dir / args.catalogue.name)
    print("Done.")


if __name__ == "__main__":
    main()
