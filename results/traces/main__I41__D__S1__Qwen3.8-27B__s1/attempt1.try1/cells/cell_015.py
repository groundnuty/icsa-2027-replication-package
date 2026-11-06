import pickle, numpy as np, os
from datetime import date, timedelta

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates = dd['base']; tgt_dates = dd['tgt']
all_dates = base_dates + tgt_dates
print("expect", len(all_dates))

# load batches
results = {}
for i in range(6):
    with open(f'/work/batch_{i}.pkl','rb') as f:
        b = pickle.load(f)
    results.update(b)
print("loaded days:", len(results))

# verify completeness
missing = [d.strftime('%Y%m%d') for d in all_dates if d.strftime('%Y%m%d') not in results]
print("missing:", len(missing), missing[:5])

SST = np.zeros((len(all_dates), 60, 60), dtype='float64')
nan_per_day = np.zeros(len(all_dates), dtype=int)
for i, d in enumerate(all_dates):
    arr = results[d.strftime('%Y%m%d')]
    assert arr.shape == (60,60)
    SST[i] = arr
    nan_per_day[i] = np.isnan(arr).sum()

np.save('/work/SST_all.npy', SST)
print("SST shape:", SST.shape, "dtype:", SST.dtype)
print("days with any NaN:", (nan_per_day>0).sum(), " of", len(all_dates))
print("days fully NaN:", (nan_per_day==3600).sum())
# target period slice
nb = len(base_dates)
print("target days NaN counts:", nan_per_day[nb:].min(), nan_per_day[nb:].max())
print("target finite range:", np.nanmin(SST[nb:]), np.nanmax(SST[nb:]))
print("baseline finite range:", np.nanmin(SST[:nb]), np.nanmax(SST[:nb]))
