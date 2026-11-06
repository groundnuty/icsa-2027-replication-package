import subprocess
code=r'''
import os, datetime as dt, numpy as np
exec(open('/work/analyse.py').read().split('# target')[0])
nanthr=np.isnan(thr[0])
T0=dt.date(2004,6,1); tdates=[T0+dt.timedelta(i) for i in range(92)]
sst=np.stack([S[d] for d in tdates]); sea=np.all(np.isfinite(sst),axis=0)
print('sea & nan thr', (sea&nanthr).sum(), 'nan thr any-doy', np.isnan(thr).any(axis=0).sum())
print('sea & nan thr any doy', (sea & np.isnan(thr).any(axis=0)).sum())
print('nan thr not sea', (~sea & nanthr).sum())
i,j=np.argwhere(sea&nanthr)[:3] if (sea&nanthr).any() else (None,None)
print(lat[i] if i is not None else '', lon[j] if j is not None else '')
print('fraction finite baseline at sea&nan cells', np.mean([np.isfinite(S[d][sea&nanthr]).mean() for d in list(S)[:50]]) if (sea&nanthr).any() else '')
'''
open('/work/chk.py','w').write(code)
r=subprocess.run('cd /work && python chk.py',shell=True,capture_output=True,text=True)
print(r.stdout[-3000:], r.stderr[-1500:] if 'Error' in r.stderr else '')