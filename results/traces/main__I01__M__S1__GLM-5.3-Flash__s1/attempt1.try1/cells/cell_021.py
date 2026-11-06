script = r'''
import numpy as np, datetime as dt

CACHE='/work/cache'
raw_t=np.load(f'{CACHE}/raw_target.npy')
thr=np.load(f'{CACHE}/thr_smooth.npy')
per_cell=np.load(f'{CACHE}/per_cell.npy')
sea=np.isfinite(raw_t).all(axis=0)
dates=[dt.date(2008,6,1)+dt.timedelta(days=k) for k in range(92)]
doy=[153+k for k in range(92)]

sst_mean = np.array([np.nanmean(raw_t[k][sea]) for k in range(92)])
thr_mean = np.array([np.nanmean(thr[d-1][sea]) for d in doy])
hot_cells = np.array([int(((raw_t[k]>=thr[d-1]) & sea).sum()) for k,d in enumerate(doy)])
sean = sea.sum()
active = per_cell.any(axis=(1,2))
print('sea cells:', sean)
for k in range(0,92,4):
    print(dates[k], f'sst={sst_mean[k]:.2f} thr={thr_mean[k]:.2f} diff={sst_mean[k]-thr_mean[k]:+.2f} hot={hot_cells[k]:4d} active={int(active[k])}')
print()
for k in range(88,92):
    print(dates[k], f'sst={sst_mean[k]:.2f} thr={thr_mean[k]:.2f} diff={sst_mean[k]-thr_mean[k]:+.2f} hot={hot_cells[k]:4d} active={int(active[k])}')
print()
print('days with hot cells > 30%:', int((hot_cells>0.3*sean).sum()))
print('max hot cells day:', dates[int(hot_cells.argmax())], int(hot_cells.max()))
print('hot_cells around event:')
for k in range(0,20):
    print(dates[k], f'diff={sst_mean[k]-thr_mean[k]:+.2f} hot={hot_cells[k]:4d} active={int(active[k])}')
'''
open('/work/diag.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/diag.py'],capture_output=True,text=True)
print(r.stdout[-4000:]); print(r.stderr[-1500:])
