import pooch

from pathlib import Path

import os
from datetime import datetime, timedelta
from pathlib import Path

import pooch
import xarray as xr
import json

from parcels._v3to4 import patch_dataset_v4_compat

__all__ = ["download_example_dataset","download_datasets"]

# When modifying existing datasets in a backwards incompatible way,
# make a new release in the repo and update the DATA_REPO_TAG to the new tag
with open(Path(__file__).parent / "../benchmarks.json", "r") as f:
    config = json.load(f)

DATA_URL = config.get("data_url", "https://surfdrive.surf.nl/index.php/s/7xlfdOFaUGDEmpD/download?path=%2F&files=")

# Keys are the dataset names. Values are the filenames in the dataset folder. Note that
# you can specify subfolders in the dataset folder putting slashes in the filename list.
# e.g.,
# "my_dataset": ["file0.nc", "folder1/file1.nc", "folder2/file2.nc"]
# my_dataset/
# ├── file0.nc
# ├── folder1/
# │   └── file1.nc
# └── folder2/
#     └── file2.nc
#
# See instructions at https://github.com/OceanParcels/parcels-data for adding new datasets
EXAMPLE_DATA_FILES = {}
for benchmark in config["benchmarks"]:
    EXAMPLE_DATA_FILES[benchmark["name"]] = [benchmark["file"]]

def _create_pooch_registry() -> dict[str, None]:
    """Collapses the mapping of dataset names to filenames into a pooch registry.

    Hashes are set to None for all files.
    """
    registry: dict[str, None] = {}
    for dataset, filenames in EXAMPLE_DATA_FILES.items():
        for filename in filenames:
            registry[f"{filename}"] = None
    return registry


POOCH_REGISTRY = _create_pooch_registry()


def _get_pooch(data_home=None):
    if data_home is None:
        data_home = os.environ.get("PARCELS_EXAMPLE_DATA")
    if data_home is None:
        data_home = pooch.os_cache("parcels-benchmarks")

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
    if dataset not in EXAMPLE_DATA_FILES:
        raise ValueError(
            f"Dataset {dataset!r} not found. Available datasets are: " + ", ".join(EXAMPLE_DATA_FILES.keys())
        )
    odie = _get_pooch(data_home=data_home)

    cache_folder = Path(odie.path)
    #dataset_folder = cache_folder / dataset

    for file_name in odie.registry:
        if file_name.startswith(dataset):
            odie.fetch(file_name)

    return cache_folder

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
    for dataset in EXAMPLE_DATA_FILES:
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