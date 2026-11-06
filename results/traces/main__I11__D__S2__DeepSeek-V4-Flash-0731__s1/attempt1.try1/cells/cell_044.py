
import numpy as np
import xarray as xr

# Load output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values  # (time, lat, lon)

# Check cell (4,51)
cell = mhw[:, 4, 51]
print("Cell (4,51) MHW pattern:")
for t in range(len(ds.time)):
    if cell[t] == 1:
        date_str = str(ds.time.values[t])[:10]
        print(f"  Day {t} ({date_str}): MHW=1")

# Verify days 17-57 are all 1
expected = np.zeros(len(ds.time), dtype=bool)
expected[17:58] = True  # days 17-57 (inclusive)
actual = cell.astype(bool)
print(f"\nMatches expected (days 17-57): {np.array_equal(expected, actual)}")
print(f"Sum: {cell.sum()}, expected: {58-17} = {58-17}")
