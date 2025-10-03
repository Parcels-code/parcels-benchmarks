import pooch

from pathlib import Path


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