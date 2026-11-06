import numpy as np, pickle, os
from datetime import date, timedelta

# baseline window dates
d0 = date(1991,12,27); d1 = date(2003,1,5)
base_dates = [d0 + timedelta(days=i) for i in range((d1-d0).days + 1)]
print("baseline window days:", len(base_dates), base_dates[0], base_dates[-1])

t0 = date(2021,6,1); t1 = date(2021,8,31)
tgt_dates = [t0 + timedelta(days=i) for i in range((t1-t0).days + 1)]
print("target days:", len(tgt_dates), tgt_dates[0], tgt_dates[-1])

all_dates = base_dates + tgt_dates
print("total files:", len(all_dates), "unique:", len(set(all_dates)))
os.makedirs('/work', exist_ok=True)
with open('/work/dates.pkl','wb') as f:
    pickle.dump(dict(base=base_dates, tgt=tgt_dates), f)
