import os
from pathlib import Path

import pooch
import typer
from pydantic import BaseModel, Field, HttpUrl, model_validator


class Dataset(BaseModel):
    """A single dataset entry in the manifest."""

    name: str = Field(..., description="Unique name for the dataset")
    file: str = Field(..., description="Filename of the dataset zip file")
    known_hash: str | None = Field(
        None, description="SHA256 hash of the file in format 'sha256:xxxxx'"
    )


class DatasetsManifest(BaseModel):
    """Root manifest structure containing all datasets."""

    data_url: HttpUrl = Field(
        ..., description="Base URL where dataset files are hosted"
    )
    datasets: list[Dataset] = Field(
        default_factory=list, description="List of available datasets"
    )

    @model_validator(mode="after")
    def validate_unique_names(self) -> "DatasetsManifest":
        """Ensure all dataset names are unique."""
        names = [dataset.name for dataset in self.datasets]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            unique_duplicates = sorted(set(duplicates))
            raise ValueError(
                f"Duplicate dataset name(s) in manifest: {', '.join(unique_duplicates)}"
            )
        return self


app = typer.Typer(add_completion=False)

PARCELS_DATADIR = os.getenv("PARCELS_DATADIR", default=None)
if PARCELS_DATADIR is not None:
    PARCELS_DATADIR = Path(PARCELS_DATADIR)

DEFAULT_MANIFEST = Path(__file__).with_name("datasets.json")


def _load_manifest(path: Path) -> DatasetsManifest:
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return DatasetsManifest.model_validate_json(f.read())


def _save_manifest(path: Path, manifest: DatasetsManifest) -> None:
    # keep stable ordering by dataset name
    manifest.datasets = sorted(manifest.datasets, key=lambda d: d.name)
    with path.open("w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))
        f.write("\n")


def _cache_dir(data_home: Path | None) -> Path:
    if data_home is None:
        return Path(pooch.os_cache("parcels-benchmarks"))
    return Path(data_home)


def _datasets_by_name(manifest: DatasetsManifest) -> dict[str, Dataset]:
    out: dict[str, Dataset] = {}
    for dataset in manifest.datasets:
        out[dataset.name] = dataset
    return out


def _create_pooch_registry(manifest: DatasetsManifest) -> dict[str, str | None]:
    """Collapses the mapping of dataset names to filenames into a pooch registry.

    Hashes are set to None for all files.
    """
    registry: dict[str, str | None] = {}
    for dataset in manifest.datasets:
        registry[dataset.file] = dataset.known_hash
    return registry


def _get_pooch(
    manifest: DatasetsManifest, data_home: Path | None = None
) -> pooch.Pooch:
    cache_dir = _cache_dir(data_home)
    registry = _create_pooch_registry(manifest)
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    return pooch.create(
        path=cache_dir,
        base_url=str(manifest.data_url),
        registry=registry,
    )


def download_example_dataset(
    dataset: str, manifest_path: Path = DEFAULT_MANIFEST, data_home: Path | None = None
) -> Path:
    """Load a dataset listed in the provided manifest

    This function provides quick access to a small number of datasets
    that are useful in documentation and testing in parcels.

    Parameters
    ----------
    dataset : str
        Name of the dataset to load.
    manifest_path: Path
        Fully qualified path to a parcels-benchmarks manifest file
    data_home : pathlike, optional
        The directory in which to cache data. If not specified, defaults to wherever
        pooch.os_cache("parcels-benchmarks") goes on your system.

    Returns
    -------
    dataset_folder : Path
        Path to the folder containing the downloaded dataset files.
    """
    manifest = _load_manifest(manifest_path)
    datasets = _datasets_by_name(manifest)

    # Dev note: `dataset` is assumed to be a folder name with netcdf files
    if dataset not in datasets:
        raise ValueError(
            f"Dataset {dataset!r} not found. Available datasets are: "
            + ", ".join(datasets.keys())
        )
    odie = _get_pooch(manifest, data_home=data_home)
    zip_name = datasets[dataset].file
    listing = odie.fetch(zip_name, processor=pooch.Unzip())

    # as pooch currently returns a file listing while we want a dir,
    # we find the common parent dir to all files
    common_parent_dir = min(
        [Path(f) for f in listing], key=lambda f: len(f.parents)
    ).parent

    return common_parent_dir


@app.command("download-all")
def download_all(
    manifest_path: Path = typer.Option(
        DEFAULT_MANIFEST, help="Path to benchmarks manifest JSON."
    ),
    data_home: Path | None = typer.Option(
        PARCELS_DATADIR, help="Override cache directory."
    ),
) -> None:
    """Download all datasets listed in benchmarks manifest file."""

    manifest = _load_manifest(manifest_path)
    datasets = _datasets_by_name(manifest)

    dataset_folders: dict[str, Path] = {}
    for dataset_name in datasets.keys():
        folder = download_example_dataset(
            dataset_name, manifest_path=manifest_path, data_home=data_home
        )
        dataset_folders[dataset_name] = folder
    return dataset_folders


@app.command("add-dataset")
def add_dataset(
    name: str = typer.Option(..., help="New dataset name to add to the manifest."),
    file: str = typer.Option(
        ..., help="Zip filename available at data_url (e.g. Foo.zip)."
    ),
    manifest: Path = typer.Option(
        DEFAULT_MANIFEST, help="Path to benchmarks manifest JSON."
    ),
    data_home: Path | None = typer.Option(
        PARCELS_DATADIR, help="Override cache directory."
    ),
) -> None:
    """
    Download a NEW dataset whose zip exists at data_url but is not yet in the manifest.

    We assume the sha256 is unknown ahead of time:
    - download with known_hash=None
    - compute sha256 of the downloaded zip
    - append {name,file,known_hash} to the manifest
    """
    m = _load_manifest(manifest)
    datasets = _datasets_by_name(m)

    if name in datasets:
        raise typer.BadParameter(f"Dataset {name!r} already exists in manifest.")

    # Also prevent duplicates by file
    existing_files = {d.file for d in m.datasets}
    if file in existing_files:
        raise typer.BadParameter(
            f"File {file!r} is already referenced in the manifest."
        )

    base_url = str(m.data_url)
    cache_dir = _cache_dir(data_home)
    url = f"{base_url}{file}"
    cache_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Downloading (no hash verification): {url}")
    # Download the zip WITHOUT verifying hash.
    result = pooch.retrieve(
        url=url,
        known_hash=None,
        path=cache_dir,
        processor=None,
    )
    typer.echo(f"  Downloaded zip -> {Path(result)}")

    digest = pooch.file_hash(Path(result))
    known_hash = f"sha256:{digest}"
    typer.echo(f"  Computed {known_hash}")

    typer.echo("Unzipping...")
    result = pooch.retrieve(
        url=url,
        known_hash=known_hash,
        path=cache_dir,
        processor=pooch.Unzip(),
    )
    files = [Path(p) for p in result]
    common_parent_dir = min(files, key=lambda p: len(p.parents)).parent
    typer.echo(f"  Unzipped -> {common_parent_dir}")

    # Append to manifest
    m.datasets.append(Dataset(name=name, file=file, known_hash=known_hash))
    _save_manifest(manifest, m)
    typer.echo(f"Added {name!r} to {manifest}")


@app.command("list")
def list_datasets(
    manifest: Path = typer.Option(
        DEFAULT_MANIFEST, help="Path to benchmarks manifest JSON."
    ),
) -> None:
    """
    List datasets in the manifest.
    """
    m = _load_manifest(manifest)
    by_name = _datasets_by_name(m)
    for name, entry in sorted(by_name.items(), key=lambda kv: kv[0]):
        typer.echo(f"{name}: {entry.file} ({entry.known_hash or 'no-hash'})")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
