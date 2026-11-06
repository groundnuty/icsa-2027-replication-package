import numpy as np, datetime as dt
dates = np.load('/tmp/dates.npy')  # datetime64[D]
data = np.load('/tmp/sst_needed.npy')
n_base = 4028
base_dates = dates[:n_base]

# day-of-year by (month, day), 1..366
md_doy = {}
cum = [0,31,59,90,120,151,181,212,243,273,304,334]  # cumulative days before month (non-leap)
for m in range(1,13):
    for day in range(1,32):
        try:
            md_doy[(m,day)] = cum[m-1] + day
        except IndexError:
            pass
md_doy[(2,29)] = 60
# sanity
for (m,d),v in md_doy.items():
    if m in (1,3) and d==1: print((m,d), '->', v)
print('(2,28)->', md_doy[(2,28)], '(2,29)->', md_doy[(2,29)], '(12,31)->', md_doy[(12,31)])

base_doy = np.array([md_doy[(int(str(d)[5:7]), int(str(d)[8:10]))] for d in base_dates])
print('baseline window DOY range:', base_doy.min(), base_doy.max())
uniq, counts = np.unique(base_doy, return_counts=True)
print('unique DOYs in baseline window:', len(uniq), 'min count', counts.min(), 'max count', counts.max())
# check day-60 pool count (29 Feb values appearing via calendar neighbours)
print('count for DOY 60:', counts[uniq==60][0] if 60 in uniq else 0)
print('count for DOY 61:', counts[uniq==61][0] if 61 in uniq else 0)
print('count for DOY 365:', counts[uniq==365][0] if 365 in uniq else 0)
print('count for DOY 366:', counts[uniq==366][0] if 366 in uniq else 0)
print('count for DOY 1:', counts[uniq==1][0] if 1 in uniq else 0)
