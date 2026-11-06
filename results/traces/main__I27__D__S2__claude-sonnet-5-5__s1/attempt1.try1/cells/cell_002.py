
la=d.latitude.values;lo=d.longitude.values
li=np.where((la>=57.83-1e-4)&(la<=59.03+1e-4))[0];oi=np.where((lo>=17.41-1e-4)&(lo<=18.61+1e-4))[0]
print(la[li],lo[oi])
s=d.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1)).load()
t=s.time.values
print(len(t),np.unique(np.diff(t)),np.isnan(s.values).mean())
