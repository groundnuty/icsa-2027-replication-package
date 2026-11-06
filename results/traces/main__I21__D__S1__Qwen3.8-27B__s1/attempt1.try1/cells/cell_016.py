import numpy as np, datetime
z = np.load('/work/region.npz')
base_dates = [datetime.date.fromisoformat(s) for s in z['base_dates']]
n = len(base_dates)
doy_yday = np.array([d.timetuple().tm_yday for d in base_dates])
ordinals = np.array([d.toordinal() for d in base_dates])
# independently reconstruct the expected date list
exp = []
d = datetime.date(1991,12,27)
while d <= datetime.date(2003,1,5):
    exp.append(d); d += datetime.timedelta(days=1)
print("len exp:", len(exp), "identical to stored:", exp == base_dates)
# check monotonic ordinal diff of 1
diffs = np.diff(ordinals)
bad = np.where(diffs != 1)[0]
print("ordinal diff !=1 positions:", bad[:20], "count:", len(bad))
for i in bad[:10]:
    print(base_dates[i], "->", base_dates[i+1], "yday:", doy_yday[i], "->", doy_yday[i+1])
