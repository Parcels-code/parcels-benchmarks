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
    from parcels.xgrid import _XGRID_AXES
    from parcels.application_kernels.interpolation import XLinear
except ImportError:
    parcelsv4 = False

DATA_ROOT = "/storage/shared/oceanparcels/input_data/CopernicusMarineService/GLOBAL_ANALYSIS_FORECAST_PHY_001_024_SMOC/"

def run_benchmark(interpolator: str, trace_memory: bool = False):
    if parcelsv4:

        def BiRectiLinear(
            field: parcels.Field,
            ti: int,
            position: dict[_XGRID_AXES, tuple[int, float | np.ndarray]],
            tau: np.float32 | np.float64,
            t: np.float32 | np.float64,
            z: np.float32 | np.float64,
            y: np.float32 | np.float64,
            x: np.float32 | np.float64,
        ):
            """Bilinear interpolation on a rectilinear grid."""
            xi, xsi = position["X"]
            yi, eta = position["Y"]

            data = field.data.data[:, :, yi:yi + 2, xi:xi + 2]
            val_t0 =(
                (1 - xsi) * (1 - eta) * data[0, 0, 0, 0]
                + xsi * (1 - eta) * data[0, 0, 0, 1]
                + xsi * eta * data[0, 0, 1, 1]
                + (1 - xsi) * eta * data[0, 0, 1, 0]
            )

            val_t1 =(
                (1 - xsi) * (1 - eta) * data[1, 0, 0, 0]
                + xsi * (1 - eta) * data[1, 0, 0, 1]
                + xsi * eta * data[1, 0, 1, 1]
                + (1 - xsi) * eta * data[1, 0, 1, 0]
            )
            return (val_t0 * (1 - tau) + val_t1 * tau)

        def PureXarrayInterp(
            field: parcels.Field,
            ti: int,
            position: dict[_XGRID_AXES, tuple[int, float | np.ndarray]],
            tau: np.float32 | np.float64,
            t: np.float32 | np.float64,
            z: np.float32 | np.float64,
            y: np.float32 | np.float64,
            x: np.float32 | np.float64,
        ):
            return field.data.interp(time=t, lon=x, lat=y).values[0]


        def NoFieldAccess(
            field: parcels.Field,
            ti: int,
            position: dict[_XGRID_AXES, tuple[int, float | np.ndarray]],
            tau: np.float32 | np.float64,
            t: np.float32 | np.float64,
            z: np.float32 | np.float64,
            y: np.float32 | np.float64,
            x: np.float32 | np.float64,
        ):
            return 0


    files = f"{DATA_ROOT}/SMOC_202101*.nc"

    lon0_expected, lat0_expected = -9.820091, -30.106716  # values from v3
    if parcelsv4:
        if interpolator == "XLinear":
            interp_method = XLinear
        elif interpolator == "BiRectiLinear":
            interp_method = BiRectiLinear
        elif interpolator == "PureXarrayInterp":
            interp_method = PureXarrayInterp
        elif interpolator == "NoFieldAccess":
            interp_method = NoFieldAccess
            lon0_expected, lat0_expected = -10, -30  # Zero interpolation, so expect initial values
        else:
            raise ValueError(f"Unknown interpolator: {interpolator}")
        ds = xr.open_mfdataset(files, concat_dim="time", combine="nested", data_vars='minimal', coords='minimal', compat='override')
        ds = ds.drop_vars(["vsdx", "vsdy", "utide", "vtide", "utotal", "vtotal"])
        ds = ds.rename({"uo": "U", "vo": "V", "longitude": "lon", "latitude": "lat"})

        xgcm_grid = parcels.xgcm.Grid(ds, coords={"X": {"left": "lon"}, "Y": {"left": "lat"}, "Z": {"left": "depth"}, "T": {"center": "time"}}, periodic=False)
        grid = parcels.xgrid.XGrid(xgcm_grid)

        U = parcels.Field("U", ds["U"], grid, interp_method=interp_method)
        V = parcels.Field("V", ds["V"], grid, interp_method=interp_method)
        U.units = parcels.GeographicPolar()
        V.units = parcels.Geographic()
        UV = parcels.VectorField("UV", U, V)

        fieldset = parcels.FieldSet([U, V, UV])
    else:
        interpolator = "v3_default"
        fieldset = parcels.FieldSet.from_netcdf(files, variables={"U": "uo", "V": "vo"}, dimensions={"time": "time", "lat": "latitude", "lon": "longitude", "depth": "depth"})

    pclass = parcels.Particle if parcelsv4 else parcels.JITParticle

    kernel = parcels.AdvectionEE

    for npart in [1, 10, 100, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000]:
        lon = np.linspace(-10, 10, npart)
        lat = np.linspace(-30, -20, npart)

        pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat)

        print(f"Running {len(lon)} particles with parcels v{4 if parcelsv4 else 3} and {interpolator} interpolator")

        if trace_memory:
            tracemalloc.start()
        else:
            start = time.time()

        pset.execute(kernel, runtime=runtime, dt=dt, verbose_progress=False)

        if trace_memory:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f"Memory usage: current={current / 1e6:.0f} MB, peak={peak / 1e6:.0f} MB")
        else:
            elapsed_time = time.time() - start
            print(f"Execution time: {elapsed_time:.2f} seconds")

        print("")
        assert np.allclose(pset[0].lon, lon0_expected, atol=1e-5), f"Expected lon {lon0_expected}, got {pset[0].lon}"
        assert np.allclose(pset[0].lat, lat0_expected, atol=1e-5), f"Expected lat {lat0_expected}, got {pset[0].lat}"


def main(args=None):
    p = ArgumentParser()

    p.add_argument(
        "-i",
        "--Interpolator",
        choices=("BiRectiLinear", "PureXarrayInterp", "NoFieldAccess"),
        default="XLinear",
    )
    p.add_argument(
        "-m",
        "--memory",
        action="store_true",
        help="Enable memory tracing (default: False)",
    )

    args = p.parse_args(args)
    run_benchmark(args.Interpolator, args.memory)


if __name__ == "__main__":
    main()
