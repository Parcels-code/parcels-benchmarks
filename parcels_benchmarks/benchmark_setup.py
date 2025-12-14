import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pooch
import sys
import xarray as xr

PARCELS_DATADIR = os.getenv("PARCELS_DATADIR", default=None)
if PARCELS_DATADIR is not None:
    PARCELS_DATADIR = Path(PARCELS_DATADIR)
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
        The directory in which to cache data. If not specified, defaults to wherever
        pooch.os_cache("parcels-benchmarks") goes on your system.

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
        The directory in which to cache data. If not specified, defaults to wherever
        pooch.os_cache("parcels-benchmarks") goes on your system.

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


def main(argv=None) -> int:
    folders = download_datasets(data_home=PARCELS_DATADIR)
    print("Downloaded datasets:")
    for name, folder in folders.items():
        print(f"  {name}: {folder}")

if __name__ == "__main__":
    raise main()

