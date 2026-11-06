
diag = r'''
import numpy as np
exec(open('/tmp/run.py').read().split("# per-cell MHW")[0])
print('T range', np.nanmin(T[:,sea]), np.nanmax(T[:,sea]), 'mean', np.nanmean(T[:,sea]))
print('thr sample', thr[152,sea][:3], thr[200,sea][:3], 'clim', clim[152,sea][:3])
doys=np.array([doy(d) for d in tgt])
ex = T - thr[doys-1]
print('exceed frac', np.mean(ex[:,sea]>=0), 'max exceed', np.nanmax(ex[:,sea]))
print('per-day mean T', np.round(np.nanmean(T[:,sea],axis=1)[::7],2))
print('per-day mean thr', np.round(np.nanmean(thr[doys-1][:,sea],axis=1)[::7],2))
print('nan in cube per day baseline', np.isnan(cube[:,sea]).sum(axis=(1,2))[:5], np.isnan(cube[:,sea]).sum())
'''
open('/tmp/diag.py','w').write(diag)
r=subprocess.run(['python','/tmp/diag.py'],capture_output=True,text=True)
print(r.stdout[-5000:], r.stderr[-3000:])
