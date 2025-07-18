import numpy as np
import parcels

runtime = np.timedelta64(10, "D")
dt = np.timedelta64(30, "m")

parcelsv4 = True
try:
    from parcels._datasets.structured.generic import datasets as datasets_structured
except ImportError:
    from tests.utils import create_fieldset_zeros_unit_mesh
    parcelsv4 = False

# create fieldset
if parcelsv4:
    ds = datasets_structured["ds_2d_left"]
    grid = parcels.xgrid.XGrid(parcels.xgcm.Grid(ds))
    U = parcels.Field("U", ds["U (A grid)"], grid, mesh_type="flat")
    V = parcels.Field("V", ds["V (A grid)"], grid, mesh_type="flat")
    fieldset = parcels.FieldSet([U, V])
else:
    fieldset = create_fieldset_zeros_unit_mesh()

pclass = parcels.Particle if parcelsv4 else parcels.JITParticle

# use a kernel that doesn't involve field access/interpolation
def DoNothing(particle, fieldset, time):
    pass

for npart in [1, 10, 50, 100, 250, 500]:
    lon = np.linspace(-10, 10, npart)
    lat = np.linspace(-30, -20, npart)

    pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat)

    print(f"Running {len(lon)} particles with parcels v{4 if parcelsv4 else 3}")
    pset.execute(DoNothing, runtime=runtime, dt=dt)
