from argparse import ArgumentParser
from pathlib import Path
import xarray as xr
import tracemalloc
import time

from glob import glob

import numpy as np

import parcels

parcelsv4 = True
try:
    from parcels.xgrid import _XGRID_AXES
    from parcels.application_kernels.interpolation import ZeroInterpolator
except ImportError:
    parcelsv4 = False

DATA_ROOT = "/Users/erik/Desktop/MOi"

def run_benchmark(trace_memory: bool = False):

    fileU = f"{DATA_ROOT}/GLO12/psy4v3r1-daily_U_2010-01-0[1-3].nc"
    filenames = {"U": glob(fileU), "V": glob(fileU.replace("_U_", "_V_")), "W": glob(fileU.replace("_U_", "_W_"))}
    mesh_mask = f"{DATA_ROOT}/domain_ORCA0083-N006/PSY4V3R1_mesh_hgr.nc"

    if parcelsv4:

        ds_u = xr.open_mfdataset(filenames["U"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["vozocrtx"]].drop_vars(
            ["nav_lon", "nav_lat"]
        )
        ds_v = xr.open_mfdataset(filenames["V"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["vomecrty"]].drop_vars(
            ["nav_lon", "nav_lat"]
        )
        ds_depth = xr.open_mfdataset(filenames["W"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["depthw"]]
        ds_mesh = xr.open_dataset(mesh_mask)[["glamf", "gphif"]].isel(t=0)

        ds = xr.merge([ds_u, ds_v, ds_depth, ds_mesh], compat="identical").rename({"vozocrtx": "U", "vomecrty": "V"}).rename({"glamf": "lon", "gphif": "lat", "time_counter": "time", "depthw": "depth"})

        xgcm_grid = parcels.xgcm.Grid(
            ds,
            coords={
                "X": {"left": "x"},
                "Y": {"left": "y"},
                "Z": {"center": "deptht", "left": "depth"},
                "T": {"center": "time"},
            },
            periodic=False,
        )
        grid = parcels.xgrid.XGrid(xgcm_grid)

        U = parcels.Field("U", ds["U"], grid, interp_method=ZeroInterpolator)
        V = parcels.Field("V", ds["V"], grid, interp_method=ZeroInterpolator)
        U.units = parcels.GeographicPolar()
        V.units = parcels.Geographic()
        UV = parcels.VectorField("UV", U, V)

        fieldset = parcels.FieldSet([U, V, UV])
    else:
        filenames = {
            "U": {"lon": mesh_mask, "lat": mesh_mask, "depth": filenames["W"][0], "data": filenames["U"]},
            "V": {"lon": mesh_mask, "lat": mesh_mask, "depth": filenames["W"][0], "data": filenames["V"]},
        }
        fieldset = parcels.FieldSet.from_netcdf(
            filenames,
            variables={"U": "vozocrtx", "V": "vomecrty"},
            dimensions={"time": "time_counter", "lat": "gphif", "lon": "glamf", "depth": "depthw"},
        )

    for npart in [1, 10, 100, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 5_000_000]:
        X, Y = np.meshgrid(
            np.linspace(75, 179, int(np.sqrt(npart))),
            np.linspace(-70, 70, int(np.sqrt(npart)))
        )
        lon = X.flatten()
        lat = Y.flatten()
        depth = np.zeros_like(lon)
        ptime = fieldset.time_interval.left

        pset = parcels.ParticleSet(fieldset=fieldset, lon=lon, lat=lat, depth=depth, time=ptime)

        print(f"Running {len(lon):_} particles with parcels v{4 if parcelsv4 else 3}")

        for i in range(2):
            if trace_memory:
                tracemalloc.start()
            else:
                start = time.time()

            # Trigger search
            fieldset.UV.eval(pset.time, pset.depth, pset.lat, pset.lon, pset)

            if trace_memory:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                print(f"Memory usage {i+1}: current={current / 1e6:.0f} MB, peak={peak / 1e6:.0f} MB")
            else:
                elapsed_time = time.time() - start
                print(f"Execution time {i+1}: {elapsed_time:.0f} seconds")

        print("")


def main(args=None):
    p = ArgumentParser()

    p.add_argument(
        "-m",
        "--memory",
        action="store_true",
        help="Enable memory tracing (default: False)",
    )

    args = p.parse_args(args)
    run_benchmark(args.memory)


if __name__ == "__main__":
    main()
