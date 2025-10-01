import time

import numpy as np
import uxarray as ux
from parcels import (
    Field,
    FieldSet,
    UXPiecewiseConstantFace,
    VectorField,
)
from parcels.uxgrid import UxGrid


def load_dataset(grid_file: str, data_path: str) -> ux.UxDataset:
    """
    Load a dataset from a NetCDF file.

    Args:
        file_path (str): The path to the directory containing NetCDF files.

    Returns:
        ux.Dataset: The loaded dataset.
    """
    # Get list of netcdf files in the directory
    return ux.open_mfdataset(grid_file, f"{data_path}/*.nc", combine="by_coords")


def cli():
    import argparse

    parser = argparse.ArgumentParser(description="Run FESOM baroclinic gyre benchmark.")
    parser.add_argument(
        "--data_path",
        type=str,
        required=True,
        help="Path(s) to the NetCDF file(s) containing the dataset.",
    )
    parser.add_argument(
        "--grid_file",
        type=str,
        required=True,
        help="Path to the grid file.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_output.csv",
        help="Path to the output CSV file for benchmark results.",
    )
    args = parser.parse_args()
    return args


def main():
    args = cli()
    data_path = args.data_path
    grid_file = args.grid_file
    _output_path = args.output

    ds = load_dataset(grid_file, data_path)
    print(ds)
    grid = UxGrid(ds.uxgrid, z=ds.coords["nz"])
    # Note that the vertical coordinate is required to be the position of the layer interfaces ("nz"), not the mid-layers ("nz1")
    U = Field(name="U", data=ds.u, grid=grid, interp_method=UXPiecewiseConstantFace)
    V = Field(name="V", data=ds.v, grid=grid, interp_method=UXPiecewiseConstantFace)
    # W = Field(name="u", data=ds.w, grid=grid, interp_method=UXPiecewiseLinearFace)
    UV = VectorField(name="UV", U=U, V=V)
    fieldset = FieldSet([UV, UV.U, UV.V])

    xmin = ds.uxgrid.node_lon.min().item()
    xmax = ds.uxgrid.node_lon.max().item()
    ymin = ds.uxgrid.node_lat.min().item()
    ymax = ds.uxgrid.node_lat.max().item()

    # Warm up (initialize spatial hash)
    lon = np.random.uniform(xmin, xmax, 1)
    lat = np.random.uniform(ymin, ymax, 1)
    depth = np.zeros_like(lon)
    fieldset.U.grid.search(depth, lat, lon)

    for npart in [1, 10, 100, 1000, 10000, 100000, 1000000]:
        lon = np.random.uniform(xmin, xmax, npart)
        lat = np.random.uniform(ymin, ymax, npart)
        depth = np.zeros_like(lon)

        start = time.time()
        fieldset.U.grid.search(depth, lat, lon)
        elapsed_time = time.time() - start
        print(f"Search time for {npart} particles: {elapsed_time:.3e} seconds")


if __name__ == "__main__":
    main()
