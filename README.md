# parcels-benchmarks

[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)

This repository houses performance benchmarks for [Parcels](https://github.com/OceanParcels/Parcels).

## Development instructions

- install Pixi
- `pixi install`
- `pixi run benchmarks`  # not functional yet

You can run the linting with `pixi run lint`

> [!IMPORTANT]
> We recommend that you download the benchmark data before running benchmarks using `pixi run python -m utils.bechmark_setup download --all`. Currently, you will need at least 50GB of disk space available to store the benchmark data.


## Contributing benchmark runs

## Adding benchmarks
You can add benchmarks by including a python script in the `benchmarks/` subdirectory. Additionally, you will need to add the benchmark details to [`benchmarks.json`](./benchmarks.json). Each benchmark entry has the following items :

```
{
      "name": "MOi-curvilinear", # Name of the benchmark
      "path": "benchmarks/benchmark_moi_curvilinear.py", # Path, relative to the root directory of this repository to the benchmark script
      "file": "Parcels_Benchmarks_MOi_data.zip", # Path, relative to the data_url, to the .zip file containing the benchmark data
      "known_hash": "f7816d872897c089eeb07a4e32b7fbcc96a0023ef01ac6c3792f88d8d8893885" # Pooch hash of the zip file (currently unused and not required)
},
```

## Data availability

Data for the benchmarks is hosted at...
