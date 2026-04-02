import intake

from . import PARCELS_BENCHMARKS_DATA_FOLDER


class Catalogs:
    CAT_EXAMPLES = intake.open_catalog(
        f"{PARCELS_BENCHMARKS_DATA_FOLDER}/surf-data/parcels-examples/catalog.yml"
    )
    CAT_BENCHMARKS = intake.open_catalog(
        f"{PARCELS_BENCHMARKS_DATA_FOLDER}/surf-data/parcels-benchmarks/catalog.yml"
    )
