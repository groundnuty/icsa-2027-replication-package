
code4 = r'''
import numpy as np, pandas as pd
exec(open('/work/s1.py').read().split("# sea cells")[0].replace("print(","(lambda *a,**k: None)("))
z=np.load('/work/thr.npz'); thr366=z['thr']; sea=z['sea']; ti=z['ti']
bm = (dates>=pd.Timestamp('1992-01-01'))&(dates<=pd.Timestamp('2002-12-31'))
bi=np.where(bm)[0]
Hb = A[bi] >= thr366[doys[bi]-1]
print('baseline frac hot (sea cells):', Hb[:,sea].mean())
Ht = A[ti] >= thr366[doys[ti]-1]
print('target frac hot (sea cells):', Ht[:,sea].mean())
print('target mean SST sea', np.nanmean(A[ti][:,sea]), 'thr mean', np.nanmean(thr366[doys[ti]-1][:,sea]))
print('baseline mean', np.nanmean(A[bi][:,sea]))
'''
open('/work/s4.py','w').write(code4)
r=subprocess.run(['python','/work/s4.py'],capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-800:])
