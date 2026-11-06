import numpy as np, datetime
z = np.load('/work/region.npz')
base_dates = [datetime.date.fromisoformat(s) for s in z['base_dates']]
n = len(base_dates)
print("n:", n, "first:", base_dates[0], "last:", base_dates[-1])
doy = np.array([d.timetuple().tm_yday for d in base_dates])
print("dtype:", doy.dtype)
b0, b1 = 5, n-6
print("T[5]:", base_dates[5], "T[4022]:", base_dates[4022])
is_anchor = np.zeros(n, bool); is_anchor[b0:b1+1] = True
print("n anchors:", is_anchor.sum())
for d in [1, 366, 365, 60, 59]:
    c = np.where(is_anchor & (doy == d))[0]
    print(d, "centers:", c, [base_dates[i] for i in c])
# check uniqueness of dates
srt = sorted(base_dates)
print("unique dates:", len(set(srt)) == n)
