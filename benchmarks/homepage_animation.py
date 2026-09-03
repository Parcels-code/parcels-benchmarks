import argparse
import numpy as np
import time
import xarray as xr
import warnings

import parcels

# Code based on the docs/user_guide/examples/tutorial_homepage_animation.md form the main Parcels repo

INPUT_FILE = "copernicusmarine_2024_globalsurface.nc"

def filter_particles_in_ocean(fieldset, lon, lat, parcels_version):
    # Filter out particles that are not in the ocean (i.e. where speed is zero)

    if parcels_version == 3:
        inocean = np.ones_like(lon, dtype=bool)
        for i in range(len(lon)):
            u, v = fieldset.UV[0, fieldset.U.grid.depth[0], lat[i], lon[i]]
            speed = np.sqrt(u**2 + v**2)
            if speed == 0:
                inocean[i] = False
    else:
        u, v = fieldset.UV[np.zeros_like(lon), np.zeros_like(lat), lat, lon]
        speed = np.sqrt(u**2 + v**2)
        inocean = speed > 0

    return inocean

def AdvectionRK2_periodic_v4(particles, fieldset):  # pragma: no cover
    """Advection of particles using second-order Runge-Kutta integration,
    keeping particles within the periodic domain [-180, 180].
    """
    (u1, v1) = fieldset.UV[particles]
    x1 = particles.x + u1 * 0.5 * particles.dt
    x1 = ((x1 + 180) % 360) - 180
    y1 = particles.y + v1 * 0.5 * particles.dt
    (u2, v2) = fieldset.UV[
        particles.t + 0.5 * particles.dt, particles.z, y1, x1, particles
    ]
    particles.dx += u2 * particles.dt
    particles.dx = ((particles.dx + particles.x + 180) % 360) - (particles.x + 180)
    particles.dy += v2 * particles.dt

def AdvectionRK2_periodic_v3(particle, fieldset, time):  # pragma: no cover
    """Advection of particles using second-order Runge-Kutta integration,
    keeping particles within the periodic domain [-180, 180].
    """
    (u1, v1) = fieldset.UV[particle]
    x1 = particle.lon + u1 * 0.5 * particle.dt
    y1 = particle.lat + v1 * 0.5 * particle.dt
    (u2, v2) = fieldset.UV[
        particle.time + 0.5 * particle.dt, particle.depth, y1, x1, particle
    ]
    particle.lon += u2 * particle.dt
    particle.lat += v2 * particle.dt


def run_global_copernicusmarine(dx, load_mode):

    parcels_version = 3 if load_mode == "parcels_v3" else 4
    if parcels_version == 3:
        fieldset = parcels.FieldSet.from_netcdf(
            INPUT_FILE,
            dimensions={"lat": "latitude", "lon": "longitude", "depth": "depth", "time": "time"},
            variables={"U": "uo", "V": "vo"},
            mesh="spherical"
        )
        fieldset.add_periodic_halo(zonal=5)
        fieldset.computeTimeChunk(0, 1)
    else:
        if load_mode == "numpy":
            ds = xr.open_dataset(INPUT_FILE)
        else:
            ds = xr.open_dataset(INPUT_FILE, chunks={})
        ds_wrap = xr.concat(
            [
                ds,
                ds.isel(longitude=slice(0, 1)).assign_coords(
                    longitude=ds.longitude.isel(longitude=slice(0, 1)) + 360
                ),
            ],
            dim="longitude",
        )
        ds = parcels.convert.copernicusmarine_to_sgrid(
            fields={"U": ds_wrap["uo"], "V": ds_wrap["vo"]}
        )
        fieldset = parcels.FieldSet.from_sgrid_conventions(ds)
        fieldset.UV.interp_method = parcels.interpolators.XFreeslip()
        if load_mode == "windowed_arrays":
            fieldset.to_windowed_arrays()
        fieldset.describe()

    lon, lat = np.meshgrid(np.arange(-179, 180, dx), np.arange(-79, 90, dx))
    lon = lon.flatten()
    lat = lat.flatten()

    inocean = filter_particles_in_ocean(fieldset, lon, lat, parcels_version)

    if parcels_version == 3:
        pset = parcels.ParticleSet(fieldset, lon=lon[inocean], lat=lat[inocean])
        kernel = AdvectionRK2_periodic_v3
    else:
        pset = parcels.ParticleSet(fieldset, x=lon[inocean], y=lat[inocean])
        kernel = AdvectionRK2_periodic_v4

    tic = time.time()
    pset.execute(
        kernel,
        dt=np.timedelta64(1, "h"),
        runtime=np.timedelta64(365, "D"),
        verbose_progress=False,
    )
    toc = time.time()
    print(f"Simulation {load_mode} with dx={dx} and {np.sum(inocean)} of particles in the ocean completed in {toc - tic:.0f} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--load-mode",
        choices=[
            "dask",
            "numpy",
            "windowed_arrays",
            "parcels_v3",
        ],
        default="dask",
        help="How to load the fieldset for the simulation.",
    )
    args = parser.parse_args()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)  #Needed for v3

        # Running dx=10 twice to account for initial loading time
        for dx in [10, 10, 5, 2, 1, 0.5, 0.1, 0.05, 0.01, 0.005, 0.001]:
            run_global_copernicusmarine(dx, args.load_mode)