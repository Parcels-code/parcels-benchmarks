# parcels-benchmarks

[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)

This repository houses performance benchmarks for [Parcels](https://github.com/OceanParcels/Parcels).

## Development instructions

This project uses a combination of [Pixi](https://pixi.sh/dev/installation/), [ASV](https://asv.readthedocs.io/), and [intake-xarray](https://github.com/intake/intake-xarray) to coordinate the setting up and running of benchmarks.

- Scripts are used to download the datasets required into the correct location
- intake-xarray is used to define data catalogues which can be easily accessed from within benchmark scripts
- ASV is used to run the benchmarks (see the [Writing the benchmarks](#writing-the-benchmarks) section).
- Pixi is used to orchestrate all the above into a convenient, user friendly workflow

You can run `pixi task list` to see the list of available tasks in the workspace.

In brief, you can set up the data and run the benchmarks by doing:

- [install Pixi](https://pixi.sh/dev/installation/) `curl -fsSL https://pixi.sh/install.sh | bash`
- `pixi install`
- `PARCELS_BENCHMARKS_DATA_FOLDER=./data pixi run benchmarks`

> [!IMPORTANT]
> Currently, you will need at least 50GB of disk space available to store the benchmark data.
> You need to be explicit to determine where the benchmark data will be saved by
> setting the `PARCELS_BENCHMARKS_DATA_FOLDER` environment variable. This
> environment variable is used in the downloading of the data and definition of
> the benchmarks.

To view the benchmark data

- `pixi run asv publish`
- `pixi run asv preview`

## Contributing benchmark runs

We value seeing how Parcels benchmarks perform on a variety of systems. When you run the benchmarks, this adds data to the `results/` subdirectory in this repository. After running the benchmarks, you can commit the changes made to the `results/` subdirectory and open a pull request to contribute your benchmark results.

### Parcels Community Members

Members of the Parcels community can contribute benchmark data using the following steps

1. [Create a fork of this repository](https://github.com/Parcels-code/parcels-benchmarks/fork)

2. Clone your fork onto your system

```
git clone --recurse-submodules git@github.com:<your-github-handle>/parcels-benchmarks.git
```

3. Run the benchmarks

```
cd ~/parcels-benchmarks
pixi run asv run
```

4. Commit your benchmark data and push the changes back to your fork, e.g.

```
git add results
git commit -m "Add benchmark data"
git push origin main
```

5. [Open a pull request from your fork](https://github.com/Parcels-code/parcels-benchmarks/compare)

## Adding benchmarks

Adding benchmarks for parcels typically involves adding a dataset and defining the benchmarks you want to run.

### Adding new data

Data is hosted remotely on a SurfDrive managed by the Parcels developers. You will need to open an issue on this repository to start the process of getting your data hosted in the shared SurfDrive.
Once your data is hosted in the shared SurfDrive, you can easily add your dataset to the benchmark dataset catalogue by modifying `catalogs/parcels-benchmarks/catalog.yml`.

In the benchmark you can now use this catalogue entry.

### Writing the benchmarks

This repository uses [ASV](https://asv.readthedocs.io/) for running benchmarks. You can add benchmarks by including a python script in the `benchmarks/` subdirectory. Within each `benchmarks/*.py` file, we ask that you define a class for the set of benchmarks you plan to run for your dataset. You can use the existing benchmarks as a good starting point for writing your benchmarks.

To learn more about writing benchmarks compatible with ASV, see the [ASV "Writing Benchmarks" documentation](https://asv.readthedocs.io/en/latest/writing_benchmarks.html)
