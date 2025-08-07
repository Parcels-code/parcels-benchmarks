from argparse import ArgumentParser
import numpy as np
import xarray as xr
import parcels
import tracemalloc
import time

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

def run_benchmark(kernel_str: str, trace_memory: bool = False):
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


    if kernel_str == "AdvectionEE":
        kernel = parcels.AdvectionEE
    elif kernel_str == "AdvectionRK4":
        kernel = parcels.AdvectionRK4
    elif kernel_str == "AdvectionRK4_thin":
        def AdvectionRK4_thin(particle, fieldset, time):  # pragma: no cover
            """Advection of particles using fourth-order Runge-Kutta integration."""
            dt = particle.dt / np.timedelta64(1, "s")  # TODO: improve API for converting dt to seconds
            (u1, v1) = fieldset.UV[particle]
            lon, lat = (particle.lon + u1 * 0.5 * dt, particle.lat + v1 * 0.5 * dt)
            (u2, v2) = fieldset.UV[time + 0.5 * particle.dt, particle.depth, lat, lon, particle]
            lon, lat = (particle.lon + u2 * 0.5 * dt, particle.lat + v2 * 0.5 * dt)
            (u3, v3) = fieldset.UV[time + 0.5 * particle.dt, particle.depth, lat, lon, particle]
            lon, lat = (particle.lon + u3 * dt, particle.lat + v3 * dt)
            (u4, v4) = fieldset.UV[time + particle.dt, particle.depth, lat, lon, particle]
            particle.dlon += (u1 + 2 * u2 + 2 * u3 + u4) / 6.0 * dt
            particle.dlat += (v1 + 2 * v2 + 2 * v3 + v4) / 6.0 * dt

        kernel = parcels.AdvectionRK4_thin

    pclass = parcels.Particle if parcelsv4 else parcels.JITParticle

    for npart in [1, 10_000, 100_000, 500_000, 1_000_000, 2_000_000]:
        lon = np.linspace(32, 50, npart)
        lat = np.ones(npart) * 30
        times = np.timedelta64(0, "s") if parcelsv4 else 0.

        pset = parcels.ParticleSet(fieldset=fieldset, pclass=pclass, lon=lon, lat=lat, time=times)

        print(f"Running {len(lon)} particles with parcels v{4 if parcelsv4 else 3} and {kernel_str}")

        if trace_memory:
            tracemalloc.start()
        else:
            start = time.time()

        pset.execute(kernel, runtime=runtime, dt=dt, verbose_progress=False)

        if trace_memory:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f"Memory usage: current={current / 1e6:.0f} MB, peak={peak / 1e6:.0f} MB")
        else:
            elapsed_time = time.time() - start
            print(f"Execution time: {elapsed_time:.0f} seconds")
        print("")

        if parcelsv4:
            pset.time_nextloop = pset.time_nextloop / np.timedelta64(1, "s")

        age = pset.time_nextloop[0] / np.timedelta64(1, "s") if parcelsv4 else pset.time_nextloop[0]
        vals = true_values(lon, age)
        assert np.allclose(pset.lon, vals[0], atol=5e-2)
        assert np.allclose(pset.lat, vals[1], atol=5e-2)

def main(args=None):
    p = ArgumentParser()
    p.add_argument(
        "-k",
        "--Kernel",
        choices=("AdvectionEE", "AdvectionRK4", "AdvectionRK4_thin"),
        default="AdvectionEE",
    )
    p.add_argument(
        "-m",
        "--memory",
        action="store_true",
        help="Enable memory tracing (default: False)",
    )

    args = p.parse_args(args)
    run_benchmark(args.Kernel, args.memory)


if __name__ == "__main__":
    main()
