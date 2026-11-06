
import sys, numpy as np, datetime as dt, warnings
sys.path.insert(0,'/work/mhw')
import common

ext, tgt, done = common.load_state()
doy_ext = np.load('/work/mhw/doy_ext.npy')
ext_dates, _ = common.all_dates()
pos = {common.datekey(d): i for i, d in enumerate(ext_dates)}

# baseline positions and their doys
b_lo, b_hi = common.datekey(dt.date(1992,1,1)), common.datekey(dt.date(2002,12,31))
rows = [i for i, d in enumerate(ext_dates) if b_lo <= common.datekey(d) <= b_hi]
rows = np.array(rows)
doyb = doy_ext[rows]
assert len(rows) == 4018, len(rows)
off = np.arange(-5, 6)
idx = {}
for d in range(1, 367):
    if d == 60: continue
    rr = rows[doyb == d]
    assert len(rr) == 11, (d, len(rr))
    idx[d] = np.sort(np.concatenate([rr[:, None] + off for o in range(-5,6)]))
    assert idx[d].size == 121
    # verify no overlap within a year (blocks 365+ apart)
print('idx built; sample d=1 first/last:', idx[1][:5], idx[1][-5:])
print('d=153 first/last:', idx[153][:5], idx[153][-5:])
print('d=59 first/last:', idx[59][:5], idx[59][-5:])
print('d=61 first/last:', idx[61][:5], idx[61][-5:])
# check that d=59 window in 1996 includes Feb 29 (pos)
i_f29 = pos[common.datekey(dt.date(1996,2,29))]
print('1996-02-29 pos', i_f29, 'in idx59?', i_f29 in set(idx[59]), 'in idx61?', i_f29 in set(idx[61]), 'in idx62?', i_f29 in set(idx[62]))
