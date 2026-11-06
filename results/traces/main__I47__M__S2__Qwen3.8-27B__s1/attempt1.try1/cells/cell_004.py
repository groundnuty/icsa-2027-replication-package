import xarray as xr
import numpy as np
import os

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
os.makedirs("work", exist_ok=True)
os.makedirs("output", exist_ok=True)

ds = xr.open_dataset(path, engine="h5netcdf")
lat_vals = ds["latitude"].values
lon_vals = ds["longitude"].values
lat_mask = (lat_vals >= np.float32(64.39)) & (lat_vals <= np.float32(65.59))
lon_mask = (lon_vals >= np.float32(23.41)) & (lon_vals <= np.float32(24.61))
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("nlat, nlon:", len(lat_idx), len(lon_idx))

time_all = ds["time"].values  # datetime64[ns]
tidx = {d: i for i, d in enumerate(time_all)}

def daterange_np(start, end):
    return np.arange(np.datetime64(start), np.datetime64(end) + np.timedelta64(1, "D"), dtype="datetime64[D]")

base_dates = daterange_np("1991-12-27", "2003-01-05")
tgt_dates = daterange_np("2019-06-01", "2019-08-31")
print("n base days:", len(base_dates), "n target days:", len(tgt_dates))

# sanity: all dates present in file
missing_b = [d for d in base_dates if d.astype("datetime64[D]") not in tidx]
missing_t = [d for d in tgt_dates if d.astype("datetime64[D]") not in tidx]
print("missing base dates:", missing_b[:5], len(missing_b))
print("missing target dates:", missing_t[:5], len(missing_t))

def read_chunk(dates):
    idx = np.array([tidx[d.astype("datetime64[D]")] for d in dates])
    out = np.empty((len(dates), len(lat_idx), len(lon_idx)), dtype=np.float32)
    CH = 500
    for s in range(0, len(dates), CH):
        slc = idx[s:s+CH]
        arr = ds["analysed_sst"].isel(time=slc, latitude=lat_idx, longitude=lon_idx).values
        out[s:s+CH] = arr
    return out

base_arr = read_chunk(base_dates)
tgt_arr = read_chunk(tgt_dates)
print("base_arr:", base_arr.shape, base_arr.dtype, "nan frac:", np.isnan(base_arr).mean().round(4))
print("tgt_arr:", tgt_arr.shape, tgt_arr.dtype, "nan frac:", np.isnan(tgt_arr).mean().round(4))

np.savez_compressed("work/sst.npz",
                    base_dates=base_dates.astype("datetime64[D]").astype(str),
                    tgt_dates=tgt_dates.astype("datetime64[D]").astype(str),
                    base_arr=base_arr, tgt_arr=tgt_arr,
                    lat=lat_vals[lat_idx], lon=lon_vals[lon_idx])
print("saved work/sst.npz", os.path.getsize("work/sst.npz"))
ds.close()
