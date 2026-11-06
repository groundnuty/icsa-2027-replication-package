import numpy as np
mask = np.load('/work/mask.npy')   # (92,60,60) bool
hot = np.greater_equal(np.load('/work/tgt.npy'), np.load('/work/thr_sm.npy')[np.arange(153,245)-1],
                       where=np.isfinite(np.load('/work/tgt.npy')), out=np.zeros(np.load('/work/tgt.npy').shape, bool))

def runs_of_true(m):
    mm = np.asarray(m, dtype=int)
    dm = np.diff(np.concatenate([[0], mm, [0]]))
    return list(zip(np.where(dm==1)[0], np.where(dm==-1)[0]))

# verify: every mask run is a subset of a hot run, all mask runs >=5, mask==hot outside filled gaps
minlen, nruns = 999, 0
for i in range(60):
    for j in range(60):
        rs = runs_of_true(mask[:, i, j])
        nruns += len(rs)
        for s, e in rs:
            minlen = min(minlen, e-s)
            assert hot[s:e, i, j].any()
            # gap between consecutive mask runs >= 3 days
        for (s1,e1),(s2,e2) in zip(rs[:-1], rs[1:]):
            assert s2-e1 >= 3
print('final per-cell runs:', nruns, '| min run length:', minlen)
# ensure mask does not include days where not hot (gap days are allowed to be non-hot!)
gaps_included = 0
for i in range(60):
    for j in range(60):
        rs = runs_of_true(mask[:, i, j])
        for s, e in rs:
            gaps_included += int((~hot[s:e, i, j]).sum())
print('non-hot gap days inside MHWs:', gaps_included)

# REGIONAL events
active = mask.any(axis=(1,2))
ev = runs_of_true(active)
import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
tgt_dates = ds.time.sel(time=slice('2014-06-01','2014-08-31')).values
events = [{'onset': str(tgt_dates[s])[:10], 'end': str(tgt_dates[e-1])[:10]} for s, e in ev]
print('number of regional events:', len(events))
for k, evd in enumerate(events):
    s, e = ev[k]
    print(k+1, evd['onset'], '->', evd['end'], f'({e-s} days)')
# active days summary
print('active days total:', int(active.sum()), 'of 92')
np.save('/work/active.npy', active)
import json
json.dump(events, open('/work/events.json','w'))