
import numpy as np, datetime as dt, os
la=np.where((lat>=56.13-1e-6)&(lat<=57.33+1e-6))[0]
lo=np.where((lon>=17.71-1e-6)&(lon<=18.91+1e-6))[0]
print(len(la),len(lo), lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
arr=np.stack([r['analysed_sst'].values[0][np.ix_(la,lo)] for r in res]).astype(np.float64)
# time arrays
tarr=np.array([np.datetime64(d) for d in dates])
np.savez('/tmp/sst_region.npz', sst=arr, dates=tarr.astype('datetime64[D]').astype(str), lat=lat[la], lon=lon[lo], latfull=lat, lonfull=lon)
print(os.path.getsize('/tmp/sst_region.npz'), arr.shape, np.nanmin(arr), np.nanmax(arr))
