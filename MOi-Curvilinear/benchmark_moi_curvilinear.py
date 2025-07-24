from argparse import ArgumentParser
from pathlib import Path
import xarray as xr

from glob import glob

import numpy as np

import parcels

runtime = np.timedelta64(2, "D")
dt = np.timedelta64(15, "m")
depth_range = range(0, 2)  # only taking upper-two depth levels

parcelsv4 = True
try:
    from parcels.xgrid import _XGRID_AXES
except ImportError:
    parcelsv4 = False

DATA_ROOT = "/storage/shared/oceanparcels/input_data/MOi"

def run_benchmark(interpolator: str):
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


    lon0_expected, lat0_expected = -10.128929, -29.721205  # values from v3 using from_netcf (so assuming A-grid!)

    fileU = f"{DATA_ROOT}/GLO12/psy4v3r1-daily_U_2010-01-0[1-3].nc"
    filenames = {"U": glob(fileU), "V": glob(fileU.replace("_U_", "_V_")), "W": glob(fileU.replace("_U_", "_W_"))}
    mesh_mask = f"{DATA_ROOT}/domain_ORCA0083-N006/PSY4V3R1_mesh_hgr.nc"

    if parcelsv4:
        if interpolator == "BiRectiLinear":
            interp_method = BiRectiLinear
        elif interpolator == "PureXarrayInterp":
            interp_method = PureXarrayInterp
        elif interpolator == "NoFieldAccess":
            interp_method = NoFieldAccess
            lon0_expected, lat0_expected = -10, -30  # Zero interpolation, so expect initial values
        else:
            raise ValueError(f"Unknown interpolator: {interpolator}")

        ds_u = xr.open_mfdataset(filenames["U"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["vozocrtx"]].drop_vars(
            ["nav_lon", "nav_lat"]
        )
        ds_v = xr.open_mfdataset(filenames["V"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["vomecrty"]].drop_vars(
            ["nav_lon", "nav_lat"]
        )
        ds_depth = xr.open_mfdataset(filenames["W"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["depthw"]]
        ds_mesh = xr.open_dataset(mesh_mask)[["glamf", "gphif"]].isel(t=0)

        ds = xr.merge([ds_u, ds_v, ds_depth, ds_mesh], compat="identical").rename({"vozocrtx": "U", "vomecrty": "V"}).rename({"glamf": "lon", "gphif": "lat", "time_counter": "time", "depthw": "depth"})
        ds = ds.isel(depth=depth_range)

        xgcm_grid = parcels.xgcm.Grid(
            ds,
            coords={
                "X": {"left": "x"},
                "Y": {"left": "y"},
                "Z": {"center": "deptht", "left": "depth"},
                "T": {"center": "time"},
            },
        )
        grid = parcels.xgrid.XGrid(xgcm_grid)

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
        fieldset = parcels.FieldSet.from_netcdf(
            filenames,
            variables={"U": "vozocrtx", "V": "vomecrty"},
            dimensions={"time": "time_counter", "lat": "gphif", "lon": "glamf", "depth": "depthw"},
            indices={"depth": depth_range},
        )

    pclass = parcels.Particle if parcelsv4 else parcels.JITParticle

    for npart in [1, 10, 100, 1000, 5000, 10000]:
        lon = np.linspace(-10, 10, npart)
        lat = np.linspace(-30, -20, npart)

        pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat)

        print(f"Running {len(lon)} particles with parcels v{4 if parcelsv4 else 3} and {interpolator} interpolator")
        pset.execute(parcels.AdvectionEE, runtime=runtime, dt=dt)

        assert np.allclose(pset[0].lon, lon0_expected, atol=1e-5), f"Expected lon {lon0_expected}, got {pset[0].lon}"
        assert np.allclose(pset[0].lat, lat0_expected, atol=1e-5), f"Expected lat {lat0_expected}, got {pset[0].lat}"


def main(args=None):
    p = ArgumentParser()

    p.add_argument(
        "-i",
        "--Interpolator",
        choices=("BiRectiLinear", "PureXarrayInterp", "NoFieldAccess"),
        default="BiRectiLinear",
    )

    args = p.parse_args(args)
    run_benchmark(args.Interpolator)


if __name__ == "__main__":
    main()
