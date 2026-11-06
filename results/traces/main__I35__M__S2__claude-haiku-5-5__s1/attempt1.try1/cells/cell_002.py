
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=59.93-1e-6)&(lat<=61.13+1e-6))[0]; lj=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
print(len(li),len(lj),lat[li[0]],lat[li[-1]],lon[lj[0]],lon[lj[-1]])
print(np.diff(lat[li][:5]), ds.time.values[:2], ds.time.size)
