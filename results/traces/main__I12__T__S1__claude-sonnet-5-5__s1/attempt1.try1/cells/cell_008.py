dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2009-06-01','2009-08-31'))
t=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(get,dates))
print(time.time()-t)
bad=[(d,r) for d,r in zip(dates,res) if r is None or isinstance(r,tuple)]
print(len(bad),bad[:5])
import pickle
ok=[(d,r.analysed_sst.values[0]) for d,r in zip(dates,res) if r is not None and not isinstance(r,tuple)]
np.savez('/tmp/d.npz',t=np.array([d.value for d,_ in ok]),a=np.stack([a for _,a in ok]),lat=res[-1].latitude.values,lon=res[-1].longitude.values)