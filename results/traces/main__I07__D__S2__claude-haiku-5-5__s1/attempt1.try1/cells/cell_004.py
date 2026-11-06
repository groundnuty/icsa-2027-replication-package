
dates = pd.DatetimeIndex(t[tidx])
A = sub.values.astype(np.float64)  # K
T,NY,NX = A.shape
# day of year per method: non-leap calendar, Feb29 -> 60
def doy(d):
    if d.month==2 and d.day==29: return 60
    nl = pd.Timestamp(2001, d.month, d.day)  # non-leap year
    return nl.dayofyear
doys = np.array([doy(d) for d in dates])
# base-period mask: 1992-01-01..2002-12-31 used as anchor dates
base_anchor = (dates>=pd.Timestamp('1992-01-01'))&(dates<=pd.Timestamp('2002-12-31'))
# Build for each anchor date (base) its doy; pool for day d: all values with date within ±5 calendar days of anchor dates with doy d.
# Equivalently, for each value date v, it belongs to pool d if exists anchor a with doy(a)=d and |v-a|<=5 days.
# Use actual calendar dates for anchors (including leap years).
anchor_dates = pd.date_range('1992-01-01','2002-12-31')
anchor_doy = np.array([doy(d) for d in anchor_dates])
pool_members = {d: [] for d in range(1,367)}
vals_idx_by_date = {}
# map each value date to index
date_to_i = {d:i for i,d in enumerate(dates)}
# for each anchor date a with doy d != 60 ... note: 60 excluded from pools
for a, d in zip(anchor_dates, anchor_doy):
    if d==60: continue
    for k in range(-5,6):
        v = a + pd.Timedelta(days=k)
        if v in date_to_i:
            pool_members[d].append(date_to_i[v])
# dedupe
pool_members = {d: np.unique(np.array(v,dtype=int)) for d,v in pool_members.items() if v}
print(len(pool_members), min(len(v) for v in pool_members.values()))
print(sorted(pool_members.keys())[:3], sorted(pool_members.keys())[-3:], 60 in pool_members)
