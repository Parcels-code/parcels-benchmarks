import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pooch
import sys
import xarray as xr

# When modifying existing datasets in a backwards incompatible way,
# make a new release in the repo and update the DATA_REPO_TAG to the new tag
BENCHMARK_DATA = [
  {
    "name": "MOi-curvilinear",
    "file": "Parcels_Benchmarks_MOi_data.zip",
    "known_hash": "f7816d872897c089eeb07a4e32b7fbcc96a0023ef01ac6c3792f88d8d8893885"
  },
  {
    "name": "FESOM-baroclinic-gyre",
    "file": "Parcels_Benchmarks_FESOM-baroclinic-gyre_v2025.10.2.2.zip",
    "known_hash": "8d849df2996e3cecf95344e6cde6ed873919d33d731b5fbed4ecacf1a57fbce3"
  }
]

DATA_URL = "https://surfdrive.surf.nl/index.php/s/7xlfdOFaUGDEmpD/download?path=%2F&files="

DATA_FILES = {}
for data in BENCHMARK_DATA:
    DATA_FILES[data["name"]] = data["file"]

def _create_pooch_registry() -> dict[str, None]:
    """Collapses the mapping of dataset names to filenames into a pooch registry.

    Hashes are set to None for all files.
    """
    registry: dict[str, None] = {}
    for data in BENCHMARK_DATA:
        registry[data["file"]] = data["known_hash"]
    return registry


POOCH_REGISTRY = _create_pooch_registry()

def _get_pooch(data_home=None):
    if data_home is None:
        data_home = pooch.os_cache("parcels-benchmarks")

    data_home.parent.mkdir(exist_ok=True)
    return pooch.create(
        path=data_home,
        base_url=DATA_URL,
        registry=POOCH_REGISTRY,
    )

def download_example_dataset(dataset: str, data_home=None):
    """Load an example dataset from the parcels website.

    This function provides quick access to a small number of example datasets
    that are useful in documentation and testing in parcels.

    Parameters
    ----------
    dataset : str
        Name of the dataset to load.
    data_home : pathlike, optional
        The directory in which to cache data. If not specified, the value
        of the ``PARCELS_EXAMPLE_DATA`` environment variable, if any, is used.
        Otherwise the default location is assigned by :func:`get_data_home`.

    Returns
    -------
    dataset_folder : Path
        Path to the folder containing the downloaded dataset files.
    """
    # Dev note: `dataset` is assumed to be a folder name with netcdf files
    if dataset not in DATA_FILES:
        raise ValueError(
            f"Dataset {dataset!r} not found. Available datasets are: " + ", ".join(DATA_FILES.keys())
        )
    odie = _get_pooch(data_home=data_home)
    print(f"dataset: {dataset}")
    print(f"Fetching: {DATA_FILES[dataset]}")
    listing = odie.fetch(DATA_FILES[dataset],processor=pooch.Unzip())

    # as pooch currently returns a file listing while we want a dir,
    # we find the common parent dir to all files
    common_parent_dir = min([Path(f) for f in listing], key=lambda f: len(f.parents)).parent

    return common_parent_dir

def download_datasets(data_home=None):
    """Download all datasets listed in the config file to the specified location.

    Parameters
    ----------
    data_home : pathlike, optional
        The directory in which to cache data. If not specified, the value
        of the ``PARCELS_EXAMPLE_DATA`` environment variable, if any, is used.
        Otherwise the default location is assigned by :func:`get_data_home`.

    Returns
    -------
    dataset_folders : dict
        Mapping of dataset names to paths to the folder containing the downloaded dataset files.
    """
    dataset_folders = {}
    for dataset in DATA_FILES:
        folder = download_example_dataset(dataset, data_home=data_home)
        dataset_folders[dataset] = folder
    return dataset_folders


def retrieve_data_dir(
    url: str = None,
    known_hash: str = None,
):
    # let pooch retrieve and get a listing of all included files
    listing = pooch.retrieve(
        url,
        processor=pooch.Unzip(),
        known_hash=known_hash,
    )

    # as pooch currently returns a file listing while we want a dir,
    # we find the common parent dir to all files
    common_parent_dir = min([Path(f) for f in listing], key=lambda f: len(f.parents)).parent

    return str(common_parent_dir)


def list_datasets():
    """Print available dataset names and their files."""
    for name, files in DATA_FILES.items():
        print(f"{name}:")
        for f in files:
            print(f"  - {f}")


def dataset_cache_root(data_home=None) -> Path:
    """Return the root cache directory used by pooch."""
    odie = _get_pooch(data_home=data_home)
    return Path(odie.path)


def dataset_paths(dataset: str, data_home=None) -> list[Path]:
    """Return full paths to all files for a given dataset (if downloaded)."""
    if dataset not in DATA_FILES:
        raise ValueError(
            f"Unknown dataset {dataset!r}. "
            f"Available datasets: {', '.join(DATA_FILES.keys())}"
        )
    root = dataset_cache_root(data_home=data_home)
    return [root / fname for fname in DATA_FILES[dataset]]


def cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parcels benchmark data helper (pooch-based downloader)."
    )

    parser.add_argument(
        "--data-home",
        type=str,
        default=None,
        help=(
            "Directory in which to cache data. Defaults to $PARCELS_EXAMPLE_DATA "
            "or the pooch cache directory if not set."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List available benchmark datasets.")

    # download
    download_parser = subparsers.add_parser(
        "download",
        help="Download one dataset or all datasets.",
    )
    download_parser.add_argument(
        "dataset",
        nargs="?",
        help="Name of the dataset to download (omit and use --all for all datasets).",
    )
    download_parser.add_argument(
        "--all",
        action="store_true",
        help="Download all datasets.",
    )

    # path
    path_parser = subparsers.add_parser(
        "path",
        help="Print local paths for a dataset's files (after download).",
    )
    path_parser.add_argument(
        "dataset",
        help="Name of the dataset.",
    )

    # retrieve-archive (optional, wraps retrieve_data_dir)
    retrieve_parser = subparsers.add_parser(
        "retrieve-archive",
        help="Retrieve and unpack an arbitrary archive via pooch.retrieve.",
    )
    retrieve_parser.add_argument("url", help="URL of the archive to retrieve.")
    retrieve_parser.add_argument(
        "--hash",
        dest="known_hash",
        default=None,
        help="Known hash for the archive (e.g. 'md5:...').",
    )

    return parser


def main(argv=None) -> int:
    parser = cli()
    args = parser.parse_args(argv)

    data_home = Path(args.data_home) if args.data_home is not None else None

    if args.command == "list":
        list_datasets()
        return 0

    if args.command == "download":
        if args.all:
            folders = download_datasets(data_home=data_home)
            print("Downloaded datasets:")
            for name, folder in folders.items():
                print(f"  {name}: {folder}")
            return 0

        if not args.dataset:
            parser.error("download: either provide DATASET or use --all")

        folder = download_example_dataset(args.dataset, data_home=data_home)
        print(f"Downloaded dataset {args.dataset!r} into {folder}")
        return 0

    if args.command == "path":
        try:
            paths = dataset_paths(args.dataset, data_home=data_home)
        except ValueError as e:
            parser.error(str(e))
        print(f"Files for dataset {args.dataset!r}:")
        for p in paths:
            print(f"  {p}")
        return 0

    if args.command == "retrieve-archive":
        local_dir = retrieve_data_dir(args.url, known_hash=args.known_hash)
        print(local_dir)
        return 0

    parser.error(f"Unknown command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())

