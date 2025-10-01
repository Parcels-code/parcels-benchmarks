import numpy as np
import uxarray as ux
from parcels import (
    Field,
    FieldSet,
    Geographic,
    GeographicPolar,
    Particle,
    ParticleSet,
    UxGrid,
    VectorField,
)
from parcels.kernels.advection import AdvectionEE
from parcels.interpolators import UXPiecewiseConstantFace




def load_dataset(grid_file: str, data_path: str) -> ux.UxDataset:
    """
    Load a dataset from a NetCDF file.

    Args:
        file_path (str): The path to the directory containing NetCDF files.

    Returns:
        ux.Dataset: The loaded dataset.
    """
    # Get list of netcdf files in the directory
    return ux.open_mfdataset(grid_file, f"{data_path}/*.nc", combine="by_coords")

def run_benchmark(
        data_path="./data", 
        grid_file="./data/mesh/fesom.mesh.diag.nc", 
        npart=1000,
        runtime=np.timedelta64(1, "D"),
        dt=np.timedelta64(2400, "s"),
        integrator=AdvectionEE,
):

    ds = load_dataset(grid_file, data_path)
    grid = UxGrid(ds.uxgrid, z=ds.coords["nz"])
    U = Field(name="U", data=ds.u, grid=grid, interp_method=UXPiecewiseConstantFace)
    V = Field(name="V", data=ds.v, grid=grid, interp_method=UXPiecewiseConstantFace)
    U.units = GeographicPolar()
    V.units = Geographic()
    UV = VectorField(name="UV", U=U, V=V) 
    fieldset = FieldSet([UV, UV.U, UV.V])

    lon = np.linspace(2.0,15.0,npart)
    lat = np.linspace(32.0,19.0,npart)

    pset = ParticleSet(fieldset=fieldset, pclass=Particle, lon=lon, lat=lat)
    pset.execute(runtime=runtime, dt=dt, pyfunc=integrator)

if __name__ == "__main__":
    run_benchmark()