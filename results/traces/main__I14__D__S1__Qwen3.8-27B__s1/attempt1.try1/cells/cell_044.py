try:
    import netCDF4
    nc = netCDF4.Dataset('/work/data/sst_s2.nc', 'r')
    print("netCDF4 opened")
    a = nc['analysed_sst']
    print("var:", a.dimensions, a.dtype)
    x = a[3647, 250, 440]
    print("scalar:", x)
    nc.close()
except Exception as e:
    print("netCDF4 failed:", type(e).__name__, e)