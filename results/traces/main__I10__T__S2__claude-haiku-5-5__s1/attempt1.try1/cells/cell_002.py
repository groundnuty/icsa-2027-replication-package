
v=ds.analysed_sst
print(v.attrs, v.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=55.67-1e-6)&(lat<=56.87+1e-6))[0]; lo=np.where((lon>=16.45-1e-6)&(lon<=17.65+1e-6))[0]
print(li.min(),li.max(),len(li),lo.min(),lo.max(),len(lo), lat[li[[0,-1]]], lon[lo[[0,-1]]])
