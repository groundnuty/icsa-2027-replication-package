with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,dates))
A=np.stack([r[0] for r in res]).astype('float64'); lat=res[0][1];lon=res[0][2]
np.save('/tmp/A.npy',A);np.save('/tmp/lat.npy',lat);np.save('/tmp/lon.npy',lon)
print(A.shape,np.nanmin(A),np.nanmax(A),np.isnan(A).mean())