for n in ['sst_19920101.nc','sst_20070601.nc','sst_20070831.nc','sst_19911227.nc','sst_20030105.nc']:
    print(n,fs.exists(P+n))
print(d.analysed_sst.attrs, float(d.analysed_sst.max()))