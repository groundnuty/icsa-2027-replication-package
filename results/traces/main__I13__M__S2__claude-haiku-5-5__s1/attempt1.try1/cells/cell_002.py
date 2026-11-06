
print(ds.analysed_sst.attrs, ds.analysed_sst.encoding)
sub=ds.sel(latitude=slice(56.09,57.29), longitude=slice(10.55,11.75))
print(sub.sizes, sub.latitude.values[[0,-1]], sub.longitude.values[[0,-1]])
