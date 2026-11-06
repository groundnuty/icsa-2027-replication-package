print(d.analysed_sst.attrs, d.analysed_sst.encoding)
lat=d.latitude.values; lon=d.longitude.values
print(np.diff(lat[:3]), np.diff(lon[:3]))
ilat=np.where((lat>=57.13-1e-6)&(lat<=58.33+1e-6))[0]; ilon=np.where((lon>=22.79-1e-6)&(lon<=23.99+1e-6))[0]
print(len(ilat),len(ilon), lat[ilat[[0,-1]]], lon[ilon[[0,-1]]])