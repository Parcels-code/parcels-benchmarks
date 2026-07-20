import copernicusmarine
import parcels
import xarray as xr
import numpy as np
import time
import argparse


def run_copernicusmarine_benchmark(load_mode="as_file"):
    copernicusmarine.login()

    ds = copernicusmarine.open_dataset(
        dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
        variables=["uo", "vo"],
        minimum_longitude=-20,
        maximum_longitude=20,
        minimum_latitude=-20,
        maximum_latitude=20,
        start_datetime="2024-01-01",
        end_datetime="2024-01-31",
        minimum_depth=0.5,
        maximum_depth=5,
        service = "arco-geo-series",
        chunk_size_limit=1,
    )
    ds = parcels.convert.copernicusmarine_to_sgrid(
        fields={"U": ds["uo"], "V": ds["vo"]}
    )

    if load_mode == "as_file":
        ds.to_netcdf("tmp.nc")
        del ds
        ds = xr.open_dataset("tmp.nc")
    elif load_mode == "ds_load":
        ds.load()

    fieldset = parcels.FieldSet.from_sgrid_conventions(ds)

    if load_mode == "streaming":
        fieldset.to_windowed_arrays()

    fieldset.describe()

    pset = parcels.ParticleSet(fieldset, x=0, y=0, z=2)
    oufile = parcels.ParticleFile(
        "tmp.parquet",
        outputdt=np.timedelta64(1, "D"),
        mode="w",
    )

    pset.execute(
        parcels.kernels.AdvectionRK2,
        dt=np.timedelta64(1, "h"),
        runtime=np.timedelta64(30, "D"),
        output_file=oufile,
    )

    # check for correctness of the benchmark result
    np.testing.assert_allclose(pset.x, -14.034891, atol=1e-2)
    np.testing.assert_allclose(pset.y, -2.1642778, atol=1e-2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--load_mode",
        choices=["as_file", "ds_load", "streaming"],
        default="streaming",
    )
    args = parser.parse_args()

    time_start = time.time()
    run_copernicusmarine_benchmark(load_mode=args.load_mode)
    time_end = time.time()
    print(f"Elapsed time: {(time_end - time_start):.2f}s")


if __name__ == "__main__":
    main()
