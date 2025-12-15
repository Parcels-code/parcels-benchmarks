import xarray as xr
import time
from glob import glob
import numpy as np
import parcels
import xgcm
from parcels.interpolators import XLinear
from parcels_benchmarks.benchmark_setup import download_example_dataset, PARCELS_DATADIR

runtime = np.timedelta64(2, "D")
dt = np.timedelta64(15, "m")

def _load_ds(datapath, chunk):
    """Helper function to load xarray dataset from datapath with or without chunking"""

    fileU = f"{datapath}/psy4v3r1-daily_U_2025-01-0[1-3].nc"
    filenames = {"U": glob(fileU), "V": glob(fileU.replace("_U_", "_V_")), "W": glob(fileU.replace("_U_", "_W_"))}
    mesh_mask = f"{datapath}/PSY4V3R1_mesh_hgr.nc"
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

    ds = xr.merge([ds_u, ds_v, ds_depth, ds_mesh], compat="identical")
    ds = ds.rename({"vozocrtx": "U", "vomecrty": "V", "glamf": "lon", "gphif": "lat", "time_counter": "time", "depthw": "depth"})
    ds.deptht.attrs["c_grid_axis_shift"] = -0.5

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
    def setup(self,interpolator,chunk,npart):
        self.datapath = download_example_dataset("MOi-curvilinear", data_home=PARCELS_DATADIR)

    def time_load_data_3d(self,interpolator,chunk,npart):
        """Benchmark that times loading the 'U' and 'V' data arrays only for 3-D"""

        # To have a reasonable runtime, we only consider the time it takes to load two time levels
        # and two depth levels (at most)
        ds = _load_ds(self.datapath,chunk)
        for j in range(min(ds.coords["deptht"].size,2)):
            for i in range(min(ds.coords["time"].size, 2)):
                u = ds["U"].isel(deptht=j,time=i).compute()
                v = ds["V"].isel(deptht=j,time=i).compute()


    def pset_execute_3d(self,interpolator,chunk,npart):
        ds = _load_ds(self.datapath,chunk)
        coords={
            "X": {"left": "x"},
            "Y": {"left": "y"},
            "Z": {"center": "deptht", "left": "depth"},
            "T": {"center": "time"},
        }

        grid = parcels._core.xgrid.XGrid(xgcm.Grid(ds, coords=coords, autoparse_metadata=False, periodic=False), mesh="spherical")

        if interpolator == "XLinear":
            interp_method = XLinear
        else:
            raise ValueError(f"Unknown interpolator: {interpolator}")

        U = parcels.Field("U", ds["U"], grid, interp_method=interp_method)
        V = parcels.Field("V", ds["V"], grid, interp_method=interp_method)
        U.units = parcels.GeographicPolar()
        V.units = parcels.Geographic()
        UV = parcels.VectorField("UV", U, V)
    
        fieldset = parcels.FieldSet([U, V, UV])
    
        pclass = parcels.Particle

        lon = np.linspace(-10, 10, npart)
        lat = np.linspace(-30, -20, npart)

        pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat)

        pset.execute(parcels.kernels.AdvectionEE, runtime=runtime, dt=dt, verbose_progress=False)

    def time_pset_execute_3d(self,interpolator,chunk,npart):
        self.pset_execute_3d(interpolator,chunk,npart)

    def peakmem_pset_execute_3d(self,interpolator,chunk,npart):
        self.pset_execute_3d(interpolator,chunk,npart)

