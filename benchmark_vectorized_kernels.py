import numpy as np
import xarray as xr
import parcels

runtime = np.timedelta64(3, "h")
dt = np.timedelta64(30, "s")

parcelsv4 = True
try:
    from parcels._datasets.structured.generated import radial_rotation_dataset
    from parcels.application_kernels.interpolation import XLinear
    from parcels.xgrid import XGrid
except ImportError:
    from docs.examples.example_radial_rotation import radial_rotation_fieldset
    parcelsv4 = False


def true_values(lon_start, age):  # Calculate the expected values for particle 2 at the endtime.
    theta = 2 * np.pi * age / (24.0 * 3600.0)
    r = lon_start - 30.0
    x = r * np.cos(theta) + 30.0
    y = -r * np.sin(theta) + 30.0
    return [x, y]


# create fieldset
if parcelsv4:
    ds = radial_rotation_dataset()
    grid = XGrid.from_dataset(ds)
    U = parcels.Field("U", ds["U"], grid, mesh_type="flat", interp_method=XLinear)
    V = parcels.Field("V", ds["V"], grid, mesh_type="flat", interp_method=XLinear)
    UV = parcels.VectorField("UV", U, V)
    fieldset = parcels.FieldSet([U, V, UV])

    def KernelEE(pset, fieldset, time):
        dt = pset.dt / np.timedelta64(1, "s")
        dx = fieldset.U.grid.lon.data[1]
        dy = fieldset.U.grid.lat.data[1]

        xi = np.floor(pset.lon / dx).astype(int)
        xsi = (pset.lon - xi * dx) / dx

        yi = np.floor(pset.lat / dy).astype(int)
        eta = (pset.lat - yi * dy) / dy

        xi = xr.DataArray(xi, dims="points")
        yi = xr.DataArray(yi, dims="points")
        # ti = xr.DataArray(np.zeros_like(xi), dims="points")
        # zi = xr.DataArray(np.zeros_like(xi), dims="points")
        U00 = fieldset.U.data.isel(XG=xi, YG=yi).values.flatten()
        U10 = fieldset.U.data.isel(XG=xi+1, YG=yi).values.flatten()
        U01 = fieldset.U.data.isel(XG=xi, YG=yi+1).values.flatten()
        U11 = fieldset.U.data.isel(XG=xi+1, YG=yi+1).values.flatten()
        u = (
            (1 - xsi) * (1 - eta) * U00
            + xsi * (1 - eta) * U10
            + (1 - xsi) * eta * U01
            + xsi * eta * U11
        )
        pset.lon += u * dt

        V00 = fieldset.V.data.isel(XG=xi, YG=yi).values.flatten()
        V10 = fieldset.V.data.isel(XG=xi+1, YG=yi).values.flatten()
        V01 = fieldset.V.data.isel(XG=xi, YG=yi+1).values.flatten()
        V11 = fieldset.V.data.isel(XG=xi+1, YG=yi+1).values.flatten()
        v = (
            (1 - xsi) * (1 - eta) * V00
            + xsi * (1 - eta) * V10
            + (1 - xsi) * eta * V01
            + xsi * eta * V11
        )
        pset.lat += v * dt

else:
    fieldset = radial_rotation_fieldset()

KernelEE = parcels.AdvectionEE

pclass = parcels.Particle if parcelsv4 else parcels.ScipyParticle

for npart in [1, 10_000, 100_000, 500_000, 1_000_000]:
    lon = np.linspace(32, 50, npart)
    lat = np.ones(npart) * 30
    time = np.timedelta64(0, "s") if parcelsv4 else 0.

    pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat, time=time)

    print(f"Running {len(lon)} particles with parcels v{4 if parcelsv4 else 3}")
    pset.execute(KernelEE, runtime=runtime, dt=dt)

    if parcelsv4:
        pset.time_nextloop = pset.time_nextloop / np.timedelta64(1, "s")

    age = pset.time_nextloop[0] / np.timedelta64(1, "s") if parcelsv4 else pset.time_nextloop[0]
    vals = true_values(lon, age)
    assert np.allclose(pset.lon, vals[0], atol=5e-2)
    assert np.allclose(pset.lat, vals[1], atol=5e-2)
