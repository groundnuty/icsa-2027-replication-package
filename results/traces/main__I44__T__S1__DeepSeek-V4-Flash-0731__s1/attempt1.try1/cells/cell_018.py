import numpy as np

# Load target SST
target_ds = xr.open_dataset('/tmp/target_data.nc')
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)

# Sea cells: finite on every day of target period
sea_mask = np.all(np.isfinite(target_sst), axis=0)  # (60, 60)
print("Sea cells:", sea_mask.sum(), "out of", sea_mask.size)
print("Land cells:", (~sea_mask).sum())
