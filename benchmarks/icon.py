import numpy as np
import uxarray as ux
from parcels import (
    convert,
    Field,
    FieldSet,
    Particle,
    ParticleSet,
    UxGrid,
    VectorField,
)
from parcels.kernels import AdvectionRK2
from parcels_benchmarks.benchmark_setup import download_example_dataset, PARCELS_DATADIR

runtime=np.timedelta64(1, "D")
dt=np.timedelta64(2400, "s")

def _load_ds(datapath):
    """Helper function to load uxarray dataset from datapath"""

    grid_file = f"{datapath}/icon_grid_O.nc"
    data_files = f"{datapath}/epoc2_010_oce_ml_1d_mean_19900102T000000Z.nc"  

    return ux.open_mfdataset(grid_file, data_files, combine="by_coords")


class ICON:
    params = (
            [10000],
            [AdvectionRK2]
        )
    param_names = [
            "npart",
            "integrator"
        ]
    def setup(self,npart,integrator):
        # Ensure the dataset is downloaded in the desired data_home
        # and obtain the path to the dataset
        self.datapath = download_example_dataset("Global ICON Data", data_home=PARCELS_DATADIR)


    def time_load_data(self,npart,integrator):
        ds = _load_ds(self.datapath)
        for i in range(min(ds.coords["time"].size, 2)):
            u = ds["u"].isel(time=i).compute()
            v = ds["v"].isel(time=i).compute()

    def pset_execute(self,npart,integrator):
        ds = _load_ds(self.datapath)
        ds = convert.icon_to_ugrid(ds)
        fieldset = FieldSet.from_ugrid_conventions(ds)

        lon = np.linspace(2.0,15.0,npart)
        lat = np.linspace(32.0,19.0,npart)

        pset = ParticleSet(fieldset=fieldset, pclass=Particle, lon=lon, lat=lat)
        pset.execute([integrator],runtime=runtime, dt=dt)

    def time_pset_execute(self,npart,integrator):
        self.pset_execute(npart,integrator)

    def peakmem_pset_execute(self,npart,integrator):
        self.pset_execute(npart,integrator)
