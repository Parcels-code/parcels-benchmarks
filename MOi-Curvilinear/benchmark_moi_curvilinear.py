from argparse import ArgumentParser
from pathlib import Path
import xarray as xr
import tracemalloc
import time

from glob import glob

import numpy as np

import parcels

runtime = np.timedelta64(2, "D")
dt = np.timedelta64(15, "m")

parcelsv4 = True
try:
    import xgcm
    from parcels.xgrid import _XGRID_AXES
    from parcels.application_kernels.interpolation import XLinear
except ImportError:
    parcelsv4 = False

DATA_ROOT = "/storage/shared/oceanparcels/input_data/MOi"

def run_benchmark(interpolator: str, trace_memory: bool = False, surface_simulation: bool =False, preload: bool = False, cycle_chunks: bool = False):

    lon0_expected, lat0_expected = -10.128929, -29.721205  # values from v3 using from_netcf (so assuming A-grid!)

    if cycle_chunks:
        xy_chunks = [64, 128, 256, 512, 1024, 2084, 32, 16, 8, 4]
        nparts = [10_000]
    else:
        xy_chunks = [256]
        nparts = [1, 10, 100, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000]
    fileU = f"{DATA_ROOT}/GLO12/psy4v3r1-daily_U_2010-01-0[1-3].nc"
    filenames = {"U": glob(fileU), "V": glob(fileU.replace("_U_", "_V_")), "W": glob(fileU.replace("_U_", "_W_"))}
    mesh_mask = f"{DATA_ROOT}/domain_ORCA0083-N006/PSY4V3R1_mesh_hgr.nc"

    for chunk in xy_chunks:
        if parcelsv4:
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
            print(ds)

            grid = parcels.xgrid.XGrid(xgcm.Grid(ds, coords=coords, autoparse_metadata=False, periodic=False))

            U = parcels.Field("U", ds["U"], grid, interp_method=interp_method)
            V = parcels.Field("V", ds["V"], grid, interp_method=interp_method)
            U.units = parcels.GeographicPolar()
            V.units = parcels.Geographic()
            UV = parcels.VectorField("UV", U, V)

            fieldset = parcels.FieldSet([U, V, UV])
        else:
            filenames = {
                "U": {"lon": mesh_mask, "lat": mesh_mask, "depth": filenames["W"][0], "data": filenames["U"]},
                "V": {"lon": mesh_mask, "lat": mesh_mask, "depth": filenames["W"][0], "data": filenames["V"]},
            }
            interpolator = "v3_default"
            if surface_simulation:
                indices={"depth": range(2)}
            else:
                indices=None

            fieldset = parcels.FieldSet.from_netcdf(
                filenames,
                variables={"U": "vozocrtx", "V": "vomecrty"},
                dimensions={"time": "time_counter", "lat": "gphif", "lon": "glamf", "depth": "depthw"},
                indices=indices,
            )

        pclass = parcels.Particle if parcelsv4 else parcels.JITParticle

        if parcelsv4 and preload:
            fieldset.U.data.load()
            fieldset.V.data.load()

        for npart in nparts:
            if cycle_chunks:
                X, Y = np.meshgrid(np.linspace(-10, 10, int(np.sqrt(npart))), np.linspace(-30, -20, int(np.sqrt(npart))))
                lon = X.flatten()
                lat = Y.flatten()
            else:
                lon = np.linspace(-10, 10, npart)
                lat = np.linspace(-30, -20, npart)

            pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat)

            print(f"Running {len(lon):_} particles on {"surface" if surface_simulation else "3D"} with parcels v{4 if parcelsv4 else 3}, chunksize {chunk} ({'preloaded' if preload else 'not preloaded'}) and {interpolator} interpolator")

            if trace_memory:
                tracemalloc.start()
            else:
                start = time.time()

            pset.execute(parcels.AdvectionEE, runtime=runtime, dt=dt, verbose_progress=False)

            if trace_memory:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                print(f"Memory usage: current={current / 1e6:.0f} MB, peak={peak / 1e6:.0f} MB")
            else:
                elapsed_time = time.time() - start
                print(f"Execution time: {elapsed_time:.0f} seconds")

            print("")

            if not cycle_chunks:
                assert np.allclose(pset[0].lon, lon0_expected, atol=1e-5), f"Expected lon {lon0_expected}, got {pset[0].lon}"
                assert np.allclose(pset[0].lat, lat0_expected, atol=1e-5), f"Expected lat {lat0_expected}, got {pset[0].lat}"


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

    p.add_argument(
        "-c",
        "--chunks",
        action="store_true",
        help="Cycle through different chunk sizes (default: False)",
    )

    args = p.parse_args(args)
    run_benchmark(args.Interpolator, args.memory, args.surface, args.preload, args.chunks)


if __name__ == "__main__":
    main()
