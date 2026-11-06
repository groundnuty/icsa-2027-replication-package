import pickle, numpy as np
from datetime import date, timedelta

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates = dd['base']; tgt_dates = dd['tgt']
nb = len(base_dates)
SST = np.load('/work/SST_all.npy')
tgt = SST[nb:]  # (92, 60, 60)

sea_mask = np.isfinite(tgt).all(axis=0)  # (60,60)
print("sea cells:", sea_mask.sum(), "of 3600")
land = ~sea_mask
# land cell persistence: are land cells NaN on all days in baseline too?
base_nan_frac = np.isnan(SST[:nb]).mean(axis=0)
print("land cells baseline NaN frac range:", base_nan_frac[land].min(), base_nan_frac[land].max())
print("sea cells baseline NaN frac range:", base_nan_frac[sea_mask].min(), base_nan_frac[sea_mask].max())
# target NaN fraction for sea cells (should be 0)
print("sea cells target NaN frac max:", np.isnan(tgt).mean(axis=0)[sea_mask].max())
np.save('/work/sea_mask.npy', sea_mask)
