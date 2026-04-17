import numpy as np
import parcels
from parcels.interpolators import XLinear

from .catalogs import Catalogs

runtime = np.timedelta64(2, "D")
dt = np.timedelta64(15, "m")


def _load_ds(chunk):
    """Helper function to load xarray dataset from catalog with or without chunking"""
    cat = Catalogs.CAT_BENCHMARKS
    chunks = {"time_counter": 1, "depth": 2, "y": chunk, "x": chunk} if chunk else None

    ds_u = (
        cat.moi_u(chunks=chunks).to_dask()[["vozocrtx"]].rename_vars({"vozocrtx": "U"})
    )
    ds_v = (
        cat.moi_v(chunks=chunks).to_dask()[["vomecrty"]].rename_vars({"vomecrty": "V"})
    )
    da_depth = cat.moi_w(chunks=chunks).to_dask()["depthw"]
    ds_mesh = cat.moi_mesh(chunks=None).read()[["glamf", "gphif"]].isel(t=0)
    ds_mesh["depthw"] = da_depth
    ds = parcels.convert.nemo_to_sgrid(fields=dict(U=ds_u, V=ds_v), coords=ds_mesh)

    return ds


class MOICurvilinear:
    """Mercator Ocean International model data based benchmark on a curvilinear grid."""

    params = (
        ["XLinear"],
        [256],
        [10000],
    )
    param_names = [
        "interpolator",
        "chunk",
        "npart",
    ]

    def time_load_data_3d(self, interpolator, chunk, npart):
        """Benchmark that times loading the 'U' and 'V' data arrays only for 3-D"""

        # To have a reasonable runtime, we only consider the time it takes to load two time levels
        # and two depth levels (at most)
        ds = _load_ds(chunk)
        for j in range(min(ds.coords["deptht"].size, 2)):
            for i in range(min(ds.coords["time"].size, 2)):
                _u = ds["U"].isel(deptht=j, time=i).compute()
                _v = ds["V"].isel(deptht=j, time=i).compute()

    def pset_execute_3d(self, interpolator, chunk, npart):
        ds = _load_ds(chunk)
        fieldset = parcels.FieldSet.from_sgrid_conventions(ds)
        if interpolator == "XLinear":
            fieldset.U.interp_method = XLinear
            fieldset.V.interp_method = XLinear
        else:
            raise ValueError(f"Unknown interpolator: {interpolator}")

        pclass = parcels.Particle

        lon = np.linspace(-10, 10, npart)
        lat = np.linspace(-30, -20, npart)
        z = np.ones(npart) * 10  # 10 m depth

        pset = parcels.ParticleSet(
            fieldset=fieldset, pclass=pclass, lon=lon, lat=lat, z=z
        )

        pset.execute(
            parcels.kernels.AdvectionEE, runtime=runtime, dt=dt, verbose_progress=False
        )

    def time_pset_execute_3d(self, interpolator, chunk, npart):
        self.pset_execute_3d(interpolator, chunk, npart)

    def peakmem_pset_execute_3d(self, interpolator, chunk, npart):
        self.pset_execute_3d(interpolator, chunk, npart)
