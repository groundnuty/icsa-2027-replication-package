
# Check which cells have NaN threshold at doy 153
nan_at_153 = np.isnan(threshold[152])
print("NaN at doy 153:", nan_at_153.sum())

# Check if these match the non-sea cells
# We need to reload the target data to check
import xarray as xr
target_start = date(2013, 6, 1)
target_end = date(2013, 8, 31)
d = target_start
target_sst = []
while d <= target_end:
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    target_sst.append(ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1])
    ds.close()
    d += timedelta(days=1)
target_sst = np.array(target_sst)

sea_mask = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_mask.sum())
print("NaN at doy 153 cells:", nan_at_153.sum())

# Check overlap
non_sea = ~sea_mask
print("Non-sea cells:", non_sea.sum())
print("NaN threshold cells not in non-sea:", (nan_at_153 & ~non_sea).sum())
print("Non-sea cells with valid threshold:", (non_sea & ~nan_at_153).sum())
