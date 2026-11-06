import h5netcdf
with h5netcdf.File('/work/sst_s2.nc','r') as f:
    for k,v in f.variables.items():
        print(k, v.dimensions, v.shape, v.dtype)
    print("global attrs:", dict(f.attrs))
    tv = f.variables['time']
    print("time attrs:", dict(tv.attrs))
    lv = f.variables['latitude']
    print("lat attrs:", dict(lv.attrs))
    ov = f.variables['analysed_sst']
    print("sst attrs:", dict(ov.attrs))
