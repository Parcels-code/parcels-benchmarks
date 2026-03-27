import os
from pathlib import Path

import intake

PARCELS_BENCHMARKS_DATA_FOLDER: str
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

try:
    PARCELS_BENCHMARKS_DATA_FOLDER = Path(os.environ["PARCELS_BENCHMARKS_DATA_FOLDER"])
except KeyError as e:
    raise RuntimeError(
        "Set the PARCELS_BENCHMARKS_DATA_FOLDER environment variable to specify where the data is/should be downloaded."
    ) from e

if not PARCELS_BENCHMARKS_DATA_FOLDER.is_absolute():
    PARCELS_BENCHMARKS_DATA_FOLDER = PROJECT_ROOT / str(PARCELS_BENCHMARKS_DATA_FOLDER)

CAT_EXAMPLES = intake.open_catalog(
    f"{PARCELS_BENCHMARKS_DATA_FOLDER}/surf-data/parcels-examples/catalog.yml"
)
CAT_BENCHMARKS = intake.open_catalog(
    f"{PARCELS_BENCHMARKS_DATA_FOLDER}/surf-data/parcels-benchmarks/catalog.yml"
)
