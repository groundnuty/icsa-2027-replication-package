import numpy as np, datetime
z = np.load('/work/region.npz')
base_dates = [datetime.date.fromisoformat(s) for s in z['base_dates']]
for i in [4022, 3657, 3292, 1831, 370]:
    d = base_dates[i]
    print(i, repr(z['base_dates'][i]), d, "yday:", d.timetuple().tm_yday, "ordinal:", d.toordinal())
# recompute doy and search for 366
doy = np.array([d.timetuple().tm_yday for d in base_dates])
idx366 = np.where(doy == 366)[0]
print("all idx with doy 366:", idx366, len(idx366))
print("doy[4022]:", doy[4022], "doy[3657]:", doy[3657], "doy[3658]:", doy[3658])
print("doy[4020:4028]:", doy[4020:4028])
print("dates[4020:4028]:", [str(base_dates[i]) for i in range(4020, 4028)])
