
print(ds.analysed_sst.attrs)
sub=ds.sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21))
print(sub.latitude.size, sub.longitude.size, sub.latitude.values[[0,-1]], sub.longitude.values[[0,-1]])
