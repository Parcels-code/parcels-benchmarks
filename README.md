# parcels-benchmarks

[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)

This repository houses performance benchmarks for [Parcels](https://github.com/OceanParcels/Parcels).

## Development instructions

- [install Pixi](https://pixi.sh/dev/installation/) `curl -fsSL https://pixi.sh/install.sh | bash`
- `pixi install`
- `pixi run asv run`

You can run the linting with `pixi run lint`

> [!IMPORTANT]
> The default path for the benchmark data is set by [pooch.os_cache](https://www.fatiando.org/pooch/latest/api/generated/pooch.os_cache.html), which typically is a subdirectory of your home directory. Currently, you will need at least 50GB of disk space available to store the benchmark data. 
> To change the location of the benchmark data cache, you can set the environment variable `PARCELS_DATADIR` to a preferred location to store the benchmark data. 


To view the benchmark data

- `pixi run asv publish`
- `pixi run asv preview`

## Contributing benchmark runs
We value seeing how Parcels benchmarks perform on a variety of systems. This repository is also used to track the performance of Parcels over time and on systems contributed by each of the developers and willing members of the Parcels community. 

When you run the benchmarks on your system, this will update the benchmark data stored in the `.asv/` directory. You can contribute those changes via a pull request.

### Parcels Developers
To contribute data as a developer who has write access to this repository,

1. Clone this repository and create a new branch, e.g.
```
git clone git@github.com:Parcels-code/parcels-benchmarks.git ~/parcels-benchmarks/
cd ~/parcels-benchmarks && git checkout -b benchmark-data
```

2. Run the benchmarks
```
pixi run asv run
```

3. Commit & push your changes
```
git add .asv
git commit
git push -u origin benchmark-data
```

4. Open a pull request

### Community members
Members of the Parcels community without write access to this repository must first [fork this repository](https://github.com/Parcels-code/parcels-benchmarks/fork). Once forked,  you can follow these steps:


1. Clone your fork of this repository, e.g.
```
git clone git@github.com:<your-github-handle>/parcels-benchmarks.git ~/parcels-benchmarks/
cd ~/parcels-benchmarks
```

2. Run the benchmarks
```
pixi run asv run
```

3. Commit & push your changes
```
git add .asv
git commit
git push
```

4. Open a pull request


## Adding benchmarks
Adding benchmarks for parcels typically involves adding a dataset and defining the benchmarks you want to run. 

Data is hosted remotely on a SurfDrive managed by the Parcels developers. You will need to open an issue on this repository to start the process of getting your data hosted in the shared SurfDrive.
Once your data is hosted, you can add an entry to the `parcels_benchmarks.benchmark_setup.DATA_FILES` list. Each entry has the following attributes

```
{
      "name": str # Name of the dataset that you can reference in the benchmarks
      "file": str, # Path, relative to the data_url, to the .zip file containing the benchmark data
      "known_hash": str | None # Pooch hash of the zip file; set to None if it is unknown
},
```

This repository uses [ASV](https://asv.readthedocs.io/) for running benchmarks. You can add benchmarks by including a python script in the `benchmarks/` subdirectory. Within each `benchmarks/*.py` file, we ask that you define a class for the set of benchmarks you plan to run for your dataset. You can use the existing benchmarks as a good starting point for writing your benchmarks.

To learn more about writing benchmarks compatible with ASV, see the [ASV "Writing Benchmarks" documentation](https://asv.readthedocs.io/en/latest/writing_benchmarks.html)
