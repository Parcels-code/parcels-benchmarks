"""Mercator Ocean International model data based benchmark on a curvilinear grid."""
from argparse import ArgumentParser
from pathlib import Path
import xarray as xr
import tracemalloc
import time

from glob import glob

import numpy as np

import parcels

import xgcm
from parcels.interpolators import XLinear

from utils import retrieve_data_dir

DATA_ROOT = retrieve_data_dir(
    url="https://surfdrive.surf.nl/index.php/s/7xlfdOFaUGDEmpD/download?path=%2F&files=Parcels_Benchmarks_MOi_data.zip",
    known_hash="f7816d872897c089eeb07a4e32b7fbcc96a0023ef01ac6c3792f88d8d8893885",
)

def time_moi_curvilinear():
    run_benchmark()
    
def run_benchmark(
        interpolator: str, trace_memory: bool = False,
        surface_simulation: bool =False, preload: bool = False,
        chunk: int = 256,
        npart: int = 10_000,
        runtime: np.timedelta64 = np.timedelta64(2, "D"),
        dt: np.timedelta64 = np.timedelta64(15, "m"),
    ):

    lon0_expected, lat0_expected = -10.128929, -29.721205  # values from v3 using from_netcf (so assuming A-grid!)

    fileU = f"{DATA_ROOT}/psy4v3r1-daily_U_2025-01-0[1-3].nc"
    filenames = {"U": glob(fileU), "V": glob(fileU.replace("_U_", "_V_")), "W": glob(fileU.replace("_U_", "_W_"))}
    mesh_mask = f"{DATA_ROOT}/PSY4V3R1_mesh_hgr.nc"

    # for chunk in xy_chunks:
    if interpolator == "XLinear":
        interp_method = XLinear
    else:
        raise ValueError(f"Unknown interpolator: {interpolator}")

    fileargs = {"concat_dim": "time_counter",
        "combine": "nested",
        "data_vars": 'minimal',
        "coords": 'minimal',
        "compat": 'override',
    }
    if chunk:
        fileargs["chunks"] = {"time_counter": 1, "depth":2, "y": chunk, "x": chunk}

    ds_u = xr.open_mfdataset(filenames["U"], **fileargs)[["vozocrtx"]].drop_vars(["nav_lon", "nav_lat"])
    ds_v = xr.open_mfdataset(filenames["V"], **fileargs)[["vomecrty"]].drop_vars(["nav_lon", "nav_lat"])
    ds_depth = xr.open_mfdataset(filenames["W"], **fileargs)[["depthw"]]
    ds_mesh = xr.open_dataset(mesh_mask)[["glamf", "gphif"]].isel(t=0)

    ds = xr.merge([ds_u, ds_v, ds_depth, ds_mesh], compat="identical").rename({"vozocrtx": "U", "vomecrty": "V"}).rename({"glamf": "lon", "gphif": "lat", "time_counter": "time", "depthw": "depth"})
    ds = xr.merge([ds_u, ds_v, ds_depth, ds_mesh], compat="identical")
    ds = ds.rename({"vozocrtx": "U", "vomecrty": "V", "glamf": "lon", "gphif": "lat", "time_counter": "time", "depthw": "depth"})
    ds.deptht.attrs["c_grid_axis_shift"] = -0.5

    coords={"X": {"left": "x"}, "Y": {"left": "y"}, "T": {"center": "time"}}

    coords={
        "X": {"left": "x"},
        "Y": {"left": "y"},
        "T": {"center": "time"},
    }
    if surface_simulation:
        ds = ds.isel(depth=0, deptht=0)
    else:
        coords["Z"] = {"center": "deptht", "left": "depth"}

    grid = parcels._core.xgrid.XGrid(xgcm.Grid(ds, coords=coords, autoparse_metadata=False, periodic=False), mesh="spherical")

    U = parcels.Field("U", ds["U"], grid, interp_method=interp_method)
    V = parcels.Field("V", ds["V"], grid, interp_method=interp_method)
    U.units = parcels.GeographicPolar()
    V.units = parcels.Geographic()
    UV = parcels.VectorField("UV", U, V)

    fieldset = parcels.FieldSet([U, V, UV])

    pclass = parcels.Particle

    if preload:
        fieldset.U.data.load()
        fieldset.V.data.load()

    # Erik: What do we do here if we only have one chunksize for the benchmark?
    # I went for the else-case for now
    #
    # if cycle_chunks:
    #     X, Y = np.meshgrid(np.linspace(-10, 10, int(np.sqrt(npart))), np.linspace(-30, -20, int(np.sqrt(npart))))
    #     lon = X.flatten()
    #     lat = Y.flatten()
    # else:
    #     lon = np.linspace(-10, 10, npart)
    #     lat = np.linspace(-30, -20, npart)
    lon = np.linspace(-10, 10, npart)
    lat = np.linspace(-30, -20, npart)

    pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat)

    print(f"Running {len(lon):_} particles on {"surface" if surface_simulation else "3D"} with parcels v4, chunksize {chunk} ({'preloaded' if preload else 'not preloaded'}) and {interpolator} interpolator")

    if trace_memory:
        tracemalloc.start()
    else:
        start = time.time()

    pset.execute(parcels.kernels.AdvectionEE, runtime=runtime, dt=dt, verbose_progress=False)

    if trace_memory:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"Memory usage: current={current / 1e6:.0f} MB, peak={peak / 1e6:.0f} MB")
    else:
        elapsed_time = time.time() - start
        print(f"Execution time: {elapsed_time:.0f} seconds")

    print("")


def main(args=None):
    p = ArgumentParser()

    p.add_argument(
        "-i",
        "--Interpolator",
        choices=("XLinear", "BiRectiLinear", "PureXarrayInterp", "NoFieldAccess"),
        default="XLinear",
    )

    p.add_argument(
        "-m",
        "--memory",
        action="store_true",
        help="Enable memory tracing (default: False)",
    )

    p.add_argument(
        "-s",
        "--surface",
        action="store_true",
        help="Run surface simulation with only 1 or 2 depth levels (default: False)",
    )

    p.add_argument(
        "-l",
        "--preload",
        action="store_true",
        help="Preload data into memory (default: False)",
    )

    # TODO: do we want CLI args for chunks and npart?

    args = p.parse_args(args)
    run_benchmark(args.Interpolator, args.memory, args.surface, args.preload)


if __name__ == "__main__":
    main()
