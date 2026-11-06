
code2 = r'''
import numpy as np, pandas as pd
exec(open('/work/s1.py').read().split("# sea cells")[0].replace("print(","(lambda *a,**k: None)("))
nanfrac = np.isnan(A).mean(axis=(1,2))
bad = np.where(nanfrac>0)[0]
print('days with any NaN:', len(bad), pd.Timestamp(dates[bad[0]]) if len(bad) else None, pd.Timestamp(dates[bad[-1]]) if len(bad) else None)
print('per-year counts of nan-days:', pd.Series(dates[bad].year).value_counts().sort_index().to_dict())
print('fraction NaN on bad days (min,max):', nanfrac[bad].min(), nanfrac[bad].max())
ptl = np.isnan(A).sum(axis=0)
print('cells with NaN at any time', (ptl>0).sum(), 'cells always NaN', (ptl==A.shape[0]).sum())
'''
open('/work/s2.py','w').write(code2)
r=subprocess.run(['python','/work/s2.py'],capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-1500:])
