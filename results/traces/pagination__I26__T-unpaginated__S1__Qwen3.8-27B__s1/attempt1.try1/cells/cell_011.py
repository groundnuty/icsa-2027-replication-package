# clean up the netcdf-writing section before running
s = open('/work/mhw_analyse.py').read()
old = """da = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_var)},
    coords={"time": np.array(time_iso, dtype="datetime64[ns]"),
            "lat": ("lat", lat.astype(np.float32)),
            "lon": ("lon", lon.astype(np.float32))},
).assign_coords(time=("time", xr.DataArray(np.array(time_iso, dtype="datetime64[ns]"), name="time")))
da = da.rename({"lat": "lat", "lon": "lon"})
# ensure coordinate dims named exactly lat/lon and time
da.to_netcdf('/work/output/mhw_mask.nc', engine="h5netcdf")"""
new = """da = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_var)},
    coords={"time": ("time", np.array(time_iso, dtype="datetime64[ns]")),
            "lat": ("lat", lat.astype(np.float32)),
            "lon": ("lon", lon.astype(np.float32))},
)
da.to_netcdf('/work/output/mhw_mask.nc', engine="h5netcdf")"""
assert old in s
s = s.replace(old, new)
open('/work/mhw_analyse.py', 'w').write(s)
print("patched")
