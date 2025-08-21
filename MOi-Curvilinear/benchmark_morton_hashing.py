from argparse import ArgumentParser
from pathlib import Path
import xarray as xr
import tracemalloc
import time

from glob import glob

import parcels

parcelsv4 = True
try:
    from parcels.xgrid import _XGRID_AXES
except ImportError:
    parcelsv4 = False
# Example Usage:
import numpy as np

DATA_ROOT = "/home/joe/Projects/Geomar-Utrecht/parcels-benchmarks/Parcels_Benchmarks_MOi_data"

def part1by2(n):
    """
    Inserts two zero bits after each of the 10 low bits of n.
    This function prepares a 10-bit integer for 3D Morton encoding.
    """
    n &= 0x000003ff  # Ensure n is within 10 bits (0-1023) using bitwise AND with masking
    n = (n | (n << 16)) & 0xff0000ff
    n = (n | (n << 8)) & 0x0300f00f
    n = (n | (n << 4)) & 0x030c30c3
    n = (n | (n << 2)) & 0x09249249
    return n

def encode_morton3d(x, y, z):
    """
    Encodes a 3D point (x, y, z) into a 3D Morton code.
    Assumes x, y, and z are non-negative integers.
    """
    #quantize coordinates 
    # Assume range of -1,1 to 0-1023
    x = ((x + 1) / 2 * 1023).astype(np.uint32)
    y = ((y + 1) / 2 * 1023).astype(np.uint32)
    z = ((z + 1) / 2 * 1023).astype(np.uint32)
    return (part1by2(z) << 2) | (part1by2(y) << 1) | part1by2(x)

def _latlon_rad_to_xyz(lat, lon):
    """Converts Spherical latitude and longitude coordinates into Cartesian x,
    y, z coordinates.
    """
    x = np.cos(lon) * np.cos(lat)
    y = np.sin(lon) * np.cos(lat)
    z = np.sin(lat)

    return x, y, z

# Lookup by querying the hash table
def query_hash_table(hash_table, morton_code):
    keys   = hash_table["keys"]
    starts = hash_table["starts"]
    counts = hash_table["counts"]
    I      = hash_table["i"]
    J      = hash_table["j"]

    pos = np.searchsorted(keys, morton_code)
    if pos == len(keys) or keys[pos] != morton_code:
        return np.empty((0, 2), dtype=int)  # not found
    start = starts[pos]
    cnt   = counts[pos]
    return np.column_stack((J[start:start+cnt], I[start:start+cnt]))

fileU = f"{DATA_ROOT}/psy4v3r1-daily_U_2025-01-0[1-3].nc"
filenames = {"U": glob(fileU), "V": glob(fileU.replace("_U_", "_V_")), "W": glob(fileU.replace("_U_", "_W_"))}
mesh_mask = f"{DATA_ROOT}/PSY4V3R1_mesh_hgr.nc"

ds_u = xr.open_mfdataset(filenames["U"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["vozocrtx"]].drop_vars(
    ["nav_lon", "nav_lat"]
)
ds_v = xr.open_mfdataset(filenames["V"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["vomecrty"]].drop_vars(
    ["nav_lon", "nav_lat"]
)
ds_depth = xr.open_mfdataset(filenames["W"], concat_dim="time_counter", combine="nested", data_vars='minimal', coords='minimal', compat='override')[["depthw"]]
ds_mesh = xr.open_dataset(mesh_mask)[["glamf", "gphif","ff"]].isel(t=0)

ds = xr.merge([ds_u, ds_v, ds_depth, ds_mesh], compat="identical").rename({"vozocrtx": "U", "vomecrty": "V"}).rename({"glamf": "lon", "gphif": "lat", "time_counter": "time", "depthw": "depth", "ff": "mask"})

xgcm_grid = parcels.xgcm.Grid(
    ds,
    coords={
        "X": {"left": "x"},
        "Y": {"left": "y"},
        "Z": {"center": "deptht", "left": "depth"},
        "T": {"center": "time"},
    },
    periodic=False,
)
grid = parcels.xgrid.XGrid(xgcm_grid,mesh="spherical")

U = parcels.Field("U", ds["U"], grid)
V = parcels.Field("V", ds["V"], grid)
U.units = parcels.GeographicPolar()
V.units = parcels.Geographic()
UV = parcels.VectorField("UV", U, V)

fieldset = parcels.FieldSet([U, V, UV])


lon = np.deg2rad(grid.lon)
lat = np.deg2rad(grid.lat)
print(f"lon.shape: {lon.shape}, lat.shape: {lat.shape}")

x, y, z = _latlon_rad_to_xyz(lat, lon)
_xbound = np.stack(
    (
        x[:-1, :-1],
        x[:-1, 1:],
        x[1:, 1:],
        x[1:, :-1],
    ),
    axis=-1,
)
_ybound = np.stack(
    (
        y[:-1, :-1],
        y[:-1, 1:],
        y[1:, 1:],
        y[1:, :-1],
    ),
    axis=-1,
)
_zbound = np.stack(
    (
        z[:-1, :-1],
        z[:-1, 1:],
        z[1:, 1:],
        z[1:, :-1],
    ),
    axis=-1,
)
# Compute centroid locations of each cells
xc = np.mean(_xbound, axis=-1)
yc = np.mean(_ybound, axis=-1)
zc = np.mean(_zbound, axis=-1)

ny, nx = xc.shape
j, i = np.indices(xc.shape) # Get the indices of the curvilinear grid
print(f"ny, nx = {ny}, {nx}")

test_lon = np.pi/4.0
test_lat = np.pi/4.0

start = time.time()
morton_codes = encode_morton3d(xc, yc, zc)
## Prepare quick lookup (hash) table for relating i,j indices to morton codes
# Sort i,j indices by morton code
order = np.argsort(morton_codes.ravel())
morton_codes_sorted = morton_codes.ravel()[order]
i_sorted = i.ravel()[order]
j_sorted = j.ravel()[order]

# Get a list of unique morton codes and their corresponding starts and counts (CSR format)
keys, starts, counts = np.unique(morton_codes_sorted, return_index=True, return_counts=True)
hash_table = {
    "keys": keys,
    "starts": starts,
    "counts": counts,
    "i": i_sorted,
    "j": j_sorted,
}
end = time.time()
print(f"Spatial hash construction time: {end - start:.4f} seconds")

n_unique_morton_codes = len(np.unique(morton_codes))
n_gridpoints = morton_codes.size
print(f"Number of unique Morton codes: {n_unique_morton_codes} / {n_gridpoints}  ({n_unique_morton_codes/n_gridpoints *100 } %)  ")

test_x = np.sin(test_lon) * np.cos(test_lat)
test_y = np.cos(test_lon) * np.cos(test_lat)
test_z = np.sin(test_lat)
test_code = encode_morton3d(np.array([test_x]), np.array([test_y]), np.array([test_z]))
print(f"The Morton code for ({test_x}, {test_y}, {test_z}) is: {test_code[0]}")

# Find the nearest point in the grid to the test point
distances = (xc - test_x)**2 + (yc - test_y)**2 + (zc - test_z)**2
min_index = np.unravel_index(np.argmin(distances), distances.shape)
print(f"The nearest grid point to ({test_x}, {test_y}, {test_z}) is at index {min_index} with coordinates ({xc[min_index]}, {yc[min_index]}, {zc[min_index]}) and Morton code {morton_codes[min_index]}")
print(f"Distance to nearest grid point: {np.sqrt(distances[min_index])}")

# Find nearest morton code
min_index = np.unravel_index(np.argmin(np.abs(morton_codes - test_code)), morton_codes.shape)
print(f"The nearest grid point by Morton code to ({test_x}, {test_y}, {test_z}) is at index {min_index} with coordinates ({xc[min_index]}, {yc[min_index]}, {zc[min_index]}) and Morton code {morton_codes[min_index]}")
print(f"Distance to nearest grid point by Morton code: {np.sqrt((xc[min_index] - test_x)**2 + (yc[min_index] - test_y)**2 + (zc[min_index] - test_z)**2)}")


# Get list of elements to search over
ijcheck = query_hash_table(hash_table, test_code[0])
j = ijcheck[:, 0]
i = ijcheck[:, 1]
distances_queried = (xc[j,i] - test_x)**2 + (yc[j,i] - test_y)**2 + (zc[j,i] - test_z)**2
min_index = np.unravel_index(np.argmin(distances_queried), distances_queried.shape)
j = j[min_index]
i = i[min_index]
print(f"The nearest grid point by Morton code to ({test_x}, {test_y}, {test_z}) is at index {j}, {i} with coordinates ({xc[j,i]}, {yc[j,i]}, {zc[j,i]}) and Morton code {morton_codes[min_index]}")
print(f"Distance to nearest grid point by Morton code (hash table query): {np.sqrt(distances_queried[min_index])}")

# Make some plots
import matplotlib.pyplot as plt
plt.imshow(morton_codes.reshape((ny,nx)), cmap='Grays')
plt.colorbar(label='Morton Code')
plt.savefig("morton_code_moi.png", dpi=600, bbox_inches='tight')
plt.close()

fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection='3d')

surf = ax.plot_surface(x, y, z, facecolors=plt.cm.Grays(morton_codes.reshape((ny,nx))/morton_codes.max()),
                           linewidth=0, antialiased=False, shade=False)
plt.savefig("morton_code_3d_moi.png", dpi=600, bbox_inches='tight')
plt.close()



