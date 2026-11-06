
lat=ds.latitude.values; lon=ds.longitude.values
ila=np.where((lat>=56.13)&(lat<=57.33))[0]; ilo=np.where((lon>=17.71)&(lon<=18.91))[0]
print(len(ila),len(ilo), lat[ila[[0,-1]]], lon[ilo[[0,-1]]])
print(ds.analysed_sst.attrs); print(ds.analysed_sst.encoding)
