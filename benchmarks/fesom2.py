import numpy as np
import uxarray as ux
import xarray as xr

from parcels import (
    FieldSet,
    Particle,
    ParticleSet,
    convert,
)
from parcels.kernels import AdvectionRK2_3D

from . import PARCELS_BENCHMARKS_DATA_FOLDER

runtime = np.timedelta64(1, "D")
dt = np.timedelta64(2400, "s")


def _load_ds():
    """Helper function to load uxarray dataset from datapath"""

    grid_file = xr.open_mfdataset(
        f"{PARCELS_BENCHMARKS_DATA_FOLDER}/surf-data/parcels-benchmarks/data/Parcelsv4_Benchmarking_data/Parcels_Benchmarks_FESOM-baroclinic-gyre/data/mesh/fesom.mesh.diag.nc"
    )
    data_files = xr.open_mfdataset(
        f"{PARCELS_BENCHMARKS_DATA_FOLDER}/surf-data/parcels-benchmarks/data/Parcelsv4_Benchmarking_data/Parcels_Benchmarks_FESOM-baroclinic-gyre/data/*.nc"
    )

    grid = ux.open_grid(grid_file)
    return ux.UxDataset(data_files, uxgrid=grid)


class FESOM2:
    params = ([10000], [AdvectionRK2_3D])
    param_names = ["npart", "integrator"]

    def time_load_data(self, npart, integrator):
        ds = _load_ds()
        for i in range(min(ds.coords["time"].size, 2)):
            _u = ds["u"].isel(time=i).compute()
            _v = ds["v"].isel(time=i).compute()

    def pset_execute(self, npart, integrator):
        ds = _load_ds()
        ds = convert.fesom_to_ugrid(ds)
        fieldset = FieldSet.from_ugrid_conventions(ds)

        lon = np.linspace(2.0, 15.0, npart)
        lat = np.linspace(32.0, 19.0, npart)

        pset = ParticleSet(fieldset=fieldset, pclass=Particle, lon=lon, lat=lat)
        pset.execute(runtime=runtime, dt=dt, pyfunc=integrator)

    def time_pset_execute(self, npart, integrator):
        self.pset_execute(npart, integrator)

    def peakmem_pset_execute(self, npart, integrator):
        self.pset_execute(npart, integrator)
