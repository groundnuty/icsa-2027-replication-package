import numpy as np, datetime as dt, time

Xall = np.load("/tmp/Xall.npy")
NB, NT = 4028, 92
X_b = Xall[:NB]; X_t = Xall[NB:]
assert X_b.shape==(NB,60,60) and X_t.shape==(NT,60,60)
Nc = 3600

# --- day-of-year mapping (leap-year calendar position) ---
def doy(d):  # d: datetime.date
    return (date(2000,d.month,d.day).toordinal() - date(2000,1,1).toordinal() + 1)
from datetime import date
base_start = date(1992,1,1); base_end = date(2002,12,31)
days = [date(1991,12,27)+dt.timedelta(i) for i in range(NB)]
doy_all = np.array([doy(d) for d in days])
print("doy range check:", doy_all.min(), doy_all.max(), "n doy60 in window:", (doy_all==60).sum())

# --- pool membership matrix B (366, NB): B[d,i] iff days[i] within +-5 days of baseline date with DOY d ---
B = np.zeros((366, NB), dtype=bool)
in_base = (doy_all >= 1) & (doy_all <= 366)  # all true
for k in range(-5, 6):
    t = np.array([days[i]+dt.timedelta(k) for i in range(NB)])
    m = (t >= base_start) & (t <= base_end)
    d_t = np.array([doy(x) for x in t])
    B[d_t[m], np.nonzero(m)[0]] = True
print("B row sums (unique d):", np.unique(B.sum(axis=1), return_counts=True))
# expected: 121 for d!=60, 0 for d=60
print("B[60].sum()==0:", B[59].sum()==0)

# quick verify with an independent definition for a couple of days
def pool_dates(d):
    s=set()
    for y in range(1992,2003):
        try: t=date(y, *[ {1:(1,1),2:(2,28),3:(3,1)}[1] ])
        except: pass
    return s
# direct check day 1: baseline dates with doy==1: Jan 1 of 1992..2002
dd = [d for d in days if doy(d)==1]
print("day-1 baseline dates:", [str(x) for x in dd])
idx1 = np.nonzero(B[0])[0]
print("day-1 window dates:", [str(days[i]) for i in idx1[:7]], "...", [str(days[i]) for i in idx1[-5:]])
