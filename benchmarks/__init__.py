import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PIXI_PROJECT_ROOT = os.environ.get("PIXI_PROJECT_ROOT")
if PIXI_PROJECT_ROOT is not None:
    PIXI_PROJECT_ROOT = Path(PIXI_PROJECT_ROOT)

PIXI_PROJECT_ROOT: Path | None

try:
    PARCELS_BENCHMARKS_DATA_FOLDER = Path(os.environ["PARCELS_BENCHMARKS_DATA_FOLDER"])
except KeyError:
    # Default to `./data`
    PARCELS_BENCHMARKS_DATA_FOLDER = Path("./data")
    logger.info("PARCELS_BENCHMARKS_DATA_FOLDER was not set. Defaulting to `./data`")

if not PARCELS_BENCHMARKS_DATA_FOLDER.is_absolute():
    if PIXI_PROJECT_ROOT is None:
        raise RuntimeError(
            "PARCELS_BENCHMARKS_DATA_FOLDER is a relative path, but PIXI_PROJECT_ROOT env variable is not set. We don't know where to store the data."
        )
    PARCELS_BENCHMARKS_DATA_FOLDER = PIXI_PROJECT_ROOT / str(
        PARCELS_BENCHMARKS_DATA_FOLDER
    )
