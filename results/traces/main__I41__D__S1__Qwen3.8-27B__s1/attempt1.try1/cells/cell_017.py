import pickle, numpy as np
from datetime import date, timedelta

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates = dd['base']; tgt_dates = dd['tgt']
all_dates = base_dates + tgt_dates

results = {}
for i, name in enumerate(['batch0.pkl','batch_1.pkl','batch_2.pkl','batch_3.pkl','batch_4.pkl','batch_5.pkl']):
    with open(f'/work/{name}','rb') as f:
        results.update(pickle.load(f))
print("loaded days:", len(results))
missing = [d.strftime('%Y%m%d') for d in all_dates if d.strftime('%Y%m%d') not in results]
print("missing:", len(missing), missing[:5])

SST = np.zeros((len(all_dates), 60, 60), dtype='float64')
for i, d in enumerate(all_dates):
    SST[i] = results[d.strftime('%Y%m%d')]
np.save('/work/SST_all.npy', SST)

nan_per_day = np.isnan(SST).sum(axis=(1,2))
nb = len(base_dates)
print("SST shape:", SST.shape, SST.dtype)
print("baseline: days with NaN:", (nan_per_day[:nb]>0).sum(), "full-NaN days:", (nan_per_day[:nb]==3600).sum())
print("target: days with NaN:", (nan_per_day[nb:]>0).sum(), "full-NaN days:", (nan_per_day[nb:]==3600).sum())
print("target finite range:", np.nanmin(SST[nb:]), np.nanmax(SST[nb:]))
print("baseline finite range:", np.nanmin(SST[:nb]), np.nanmax(SST[:nb]))
