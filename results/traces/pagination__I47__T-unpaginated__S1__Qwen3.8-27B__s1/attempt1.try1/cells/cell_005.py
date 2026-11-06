
try:
    import xarray as xr
    print("xarray ok", xr.__version__)
except Exception as e:
    print("xarray import failed:", e)
try:
    import netCDF4
    print("netCDF4 ok", netCDF4.__version__)
except Exception as e:
    print("netCDF4 import failed:", e)
