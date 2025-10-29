# parcels-benchmarks

[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)

This repository houses performance benchmarks for [Parcels](https://github.com/OceanParcels/Parcels).

## Development instructions

- install Pixi
- `pixi install`
- `pixi run benchmarks`  # not functional yet

You can run the linting with `pixi run lint`

> [!IMPORTANT]
> Keep in mind: The platform which you run the benchmarks is very important as some platforms may not have access to the data required by the benchmarks, and performance will change based on the compute and memory resources of the platform.

## Running benchmarks
Presently, to run benchmarks, you can do `pixi run python ./run_benchmarks` . This main program will take care of downloading all necessary data required for all benchmarks and will attempt to capture all relevant system information, including cpu, memory, and disk details. 

> [!NOTE]
> When capturing disk information, we only consider the physical hardware that is hosting the benchmark data. The location of the benchmark data can be changed using the `os_cache_parentdir` field defined in the `benchmarks.json`.

Running the benchmarks will append results to the [`benchmark_results.jsonl`](./benchmark_results.jsonl) file included in this repository.

## Contributing benchmark runs
Parcels developers and maintainers currently track benchmark performance in a [centralized Google Sheet](https://docs.google.com/spreadsheets/d/1GcM_i7ROwIblnura0zgv7CS31HfISrzPRyhbN89Q8zs). Visualizations of the results can be seen in the (public) [Parcels Benchmarks Lookerstudio report](https://lookerstudio.google.com/reporting/940bd8cd-0208-4152-87c0-4f5137b1ddc6). The aim of this data collection is to provide Parcels users with a feel for the expected runtimes and memory requirements for running various Parcels benchmarks. Additionally, tracking this data over time helps Parcels developers ensure performance regressions are not introduced as development progresses.

Developers and maintainers with write access to the centralized Google Sheet can push their benchmark results by running the benchmarks locally with 
```
pixi run python ./run_benchmarks --upload
```

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
