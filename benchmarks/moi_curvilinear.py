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
from utils.benchmark_setup import download_example_dataset

runtime = np.timedelta64(2, "D")
dt = np.timedelta64(15, "m")

class MOICurvilinear:
    """Mercator Ocean International model data based benchmark on a curvilinear grid."""

    params = ( 
            [None],
            ["XLinear"],
            [256],
            [10000],
    )
    param_names = [
            "data_home",
            "interpolator",
            "chunk",
            "npart",
        ]
    def setup(self,data_home,interpolator,chunk,npart):
        # Ensure the dataset is downloaded in the desired data_home
        # and obtain the path to the dataset
        datapath = download_example_dataset("MOi-curvilinear", data_home=data_home)

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

        self.ds = xr.merge([ds_u, ds_v, ds_depth, ds_mesh], compat="identical")
        self.ds = self.ds.rename({"vozocrtx": "U", "vomecrty": "V", "glamf": "lon", "gphif": "lat", "time_counter": "time", "depthw": "depth"})
        self.ds.deptht.attrs["c_grid_axis_shift"] = -0.5
        self.coords={
            "X": {"left": "x"},
            "Y": {"left": "y"},
            "T": {"center": "time"},
        }

        if interpolator == "XLinear":
            self.interp_method = XLinear
        else:
            raise ValueError(f"Unknown interpolator: {interpolator}")


    def teardown(self,data_home,interpolator,chunk,npart):
        del self.ds


    def time_load_data_3d(self,data_home,interpolator,chunk,npart):
        """Benchmark that times loading the 'U' and 'V' data arrays only for 3-D"""
        self.ds["U"].load()
        self.ds["V"].load()

    def time_load_data_2d(self,data_home,interpolator,chunk,npart):
        """Benchmark that times loading the 'U' and 'V' data arrays only for 3-D"""
        self.ds["U"].isel(depth=0, deptht=0).load()
        self.ds["V"].isel(depth=0, deptht=0).load()

    def time_pset_execute_3d(self,data_home,interpolator,chunk,npart):
        self.coords["Z"] = {"center": "deptht", "left": "depth"}

        ds = self.ds

        grid = parcels._core.xgrid.XGrid(xgcm.Grid(ds, coords=self.coords, autoparse_metadata=False, periodic=False), mesh="spherical")

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
        
    def time_pset_execute_surface(self,data_home,interpolator,chunk,npart): 
        ds = self.ds.isel(depth=0, deptht=0)

        grid = parcels._core.xgrid.XGrid(xgcm.Grid(ds, coords=coords, autoparse_metadata=False, periodic=False), mesh="spherical")
    
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

    def mem_pset_execute_3d(self,data_home,interpolator,chunk,npart):
        self.coords["Z"] = {"center": "deptht", "left": "depth"}

        ds = self.ds

        grid = parcels._core.xgrid.XGrid(xgcm.Grid(ds, coords=self.coords, autoparse_metadata=False, periodic=False), mesh="spherical")

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
        
    def mem_pset_execute_surface(self,data_home,interpolator,chunk,npart): 
        ds = self.ds.isel(depth=0, deptht=0)

        grid = parcels._core.xgrid.XGrid(xgcm.Grid(ds, coords=coords, autoparse_metadata=False, periodic=False), mesh="spherical")
    
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
