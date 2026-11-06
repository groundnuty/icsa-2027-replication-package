import numpy as np, datetime
z = np.load('/work/region.npz'); m = np.load('/work/mhw.npz')
mhw, active, sea, reg = m['mhw'], m['active'], m['sea'], m['reg']
dates = [datetime.date.fromisoformat(x) for x in z['tgt_dates']]
print("reg:", reg)
cnt = mhw.sum(axis=1)
for i in range(92):
    bar = '#'*min(cnt[i]//50, 60)
    print(dates[i].isoformat(), f"{cnt[i]:5d}", bar)

# pick the cell with the longest MHW span and show its hot pattern + runs
mhw2 = mhw.reshape(92, 60, 60)
spans = mhw2.any(axis=0)
idx = np.unravel_index(np.argmax(mhw2.sum(axis=0).ravel()), (60,60))
r, c = idx
col = r*60+c
print("\ncell at lat", z['lat'][r], "lon", z['lon'][c], "total MHW days:", int(mhw[:, col].sum()))
hot = m['hot'] if 'hot' in m.files else None
# recompute hot for this cell
import numpy as _np
s = _np.load('/work/doy_stats.npz')
tgt3 = z['tgt_sst'].reshape(92, 3600)
thr_t = s['sm_thresh'].reshape(366, 3600)[s['target_doy']-1, :]
hotc = (tgt3[:, col] >= thr_t[:, col])
def runs(x):
    out=[]; i=0
    while i < len(x):
        if x[i]:
            j=i
            while j+1<len(x) and x[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
print("hot runs (day idx, inclusive):", runs(hotc))
print("mhw days in cell:", np.where(mhw[:, col])[0])
print("hot pattern (J=Jul):", ''.join('H' if h else ('.' if not mhw[0,i] else 'g') for i,h in enumerate(hotc))[0:92])
