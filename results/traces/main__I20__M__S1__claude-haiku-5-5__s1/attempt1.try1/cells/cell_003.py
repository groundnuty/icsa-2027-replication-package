print(ds.attrs['comment'])
lat=ds.latitude.values.astype(float); lon=ds.longitude.values.astype(float)
li=np.where((lat>=57.33-1e-6)&(lat<=58.53+1e-6))[0]; lj=np.where((lon>=9.03-1e-6)&(lon<=10.23+1e-6))[0]
print(len(li),len(lj), lat[li[0]],lat[li[-1]],lon[lj[0]],lon[lj[-1]])
print(ds.analysed_sst.encoding)