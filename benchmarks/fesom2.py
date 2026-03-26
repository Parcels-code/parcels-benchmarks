import numpy as np
import uxarray as ux

from parcels import (
    FieldSet,
    Particle,
    ParticleSet,
    convert,
)
from parcels.kernels import AdvectionRK2_3D
from parcels_benchmarks.benchmark_setup import PARCELS_DATADIR, download_dataset

runtime = np.timedelta64(1, "D")
dt = np.timedelta64(2400, "s")


def _load_ds(datapath):
    """Helper function to load uxarray dataset from datapath"""

    grid_file = f"{datapath}/mesh/fesom.mesh.diag.nc"
    data_files = f"{datapath}/*.nc"
    return ux.open_mfdataset(grid_file, data_files, combine="by_coords")


class FESOM2:
    params = ([10000], [AdvectionRK2_3D])
    param_names = ["npart", "integrator"]

    def setup(self, npart, integrator):
        # Ensure the dataset is downloaded in the desired data_home
        # and obtain the path to the dataset
        self.datapath = download_dataset(
            "FESOM-baroclinic-gyre", data_home=PARCELS_DATADIR
        )

    def time_load_data(self, npart, integrator):
        ds = _load_ds(self.datapath)
        for i in range(min(ds.coords["time"].size, 2)):
            _u = ds["u"].isel(time=i).compute()
            _v = ds["v"].isel(time=i).compute()

    def pset_execute(self, npart, integrator):
        ds = _load_ds(self.datapath)
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
