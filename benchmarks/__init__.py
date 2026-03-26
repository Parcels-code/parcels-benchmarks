import os
from pathlib import Path
import intake

try:
    PARCELS_BENCHMARKS_DATA_FOLDER = Path(os.environ["PARCELS_BENCHMARKS_DATA_FOLDER"])
except KeyError as e:
    raise RuntimeError("Set the PARCELS_BENCHMARKS_DATA_FOLDER environment variable to specify where the data is/should be downloaded.") from e

CAT_EXAMPLES = intake.open_catalog('surf-data/parcels-examples/catalog.yml')
CAT_BENCHMARKS = intake.open_catalog('surf-data/parcels-benchmarks/catalog.yml')