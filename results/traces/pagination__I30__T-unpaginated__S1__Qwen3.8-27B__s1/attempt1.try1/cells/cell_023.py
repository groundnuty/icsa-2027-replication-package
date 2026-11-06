
import sys, numpy as np, datetime as dt
sys.path.insert(0,'/work/mhw')
import common

ext, tgt, done = common.load_state()
doy_ext = np.load('/work/mhw/doy_ext.npy')
ext_dates, _ = common.all_dates()
pos = {common.datekey(d): i for i, d in enumerate(ext_dates)}

b_lo, b_hi = common.datekey(dt.date(1992,1,1)), common.datekey(dt.date(2002,12,31))
rows = np.array([i for i, d in enumerate(ext_dates) if b_lo <= common.datekey(d) <= b_hi])
doyb = doy_ext[rows]
assert len(rows) == 4018, len(rows)

idx = {}
for d in range(1, 367):
    if d == 60: continue
    rr = rows[doyb == d]
    assert len(rr) == 11, (d, len(rr))
    idx[d] = np.sort(np.concatenate([rr + o for o in range(-5, 6)]))
    assert idx[d].size == 121
    assert np.all(np.diff(idx[d]) >= 0)
np.save('/work/mhw/idx.pkl.npy', np.array([0]), allow_pickle=False)  # placeholder
import pickle
with open('/work/mhw/idx.pkl','wb') as f: pickle.dump(idx, f)

i_f29 = pos[common.datekey(dt.date(1996,2,29))]
print('1996-02-29 pos', i_f29,
      'in idx59:', i_f29 in set(idx[59]),
      'in idx61:', i_f29 in set(idx[61]),
      'in idx62:', i_f29 in set(idx[62]),
      'in idx66:', i_f29 in set(idx[66]),
      'in idx55:', i_f29 in set(idx[55]))
print('d=1 idx:', idx[1][:11], '...')
print('d=153 head:', idx[153][:6], 'tail:', idx[153][-6:])
print('d=244 head:', idx[244][:6], 'tail:', idx[244][-6:])
