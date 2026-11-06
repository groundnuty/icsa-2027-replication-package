import numpy as np, datetime as dt

Z = np.load("/tmp/mhw/loaded.npz")
Vb, Vt = Z["Vb"], Z["Vt"]
BASE_START = dt.date(1991,12,27)
leap_month = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
for m in range(1,13):
    s = 1
    for mm in range(1,m): s += leap_month[mm-1]
    for day in range(1, leap_month[m-1]+1):
        doy_of[(m,day)] = s + day - 1
BL_START, BL_END = dt.date(1992,1,1), dt.date(2002,12,31)
bl_dates = [BL_START + dt.timedelta(days=i) for i in range((BL_END-BL_START).days+1)]
bl_ord = np.array([(dd.toordinal()-BASE_START.toordinal()) for dd in bl_dates])
bl_doy = np.array([doy_of[(dd.month,dd.day)] for dd in bl_dates])
pools = {}
for d in range(1, 367):
    if d == 60: continue
    m = bl_doy == d
    pools[d] = np.unique(bl_ord[m][:,None] + np.arange(-5,6)[None,:])

THR = np.full((366, 60, 60), np.nan)
CLI = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    x = Vb[pools[d]]           # (121, 60, 60)
    THR[d-1] = np.nanquantile(x, 0.90, method="hazen", axis=0)
    CLI[d-1] = np.nanmean(x, axis=0)
# day 60 = mean of 59 and 61
THR[59] = np.mean(np.stack([THR[58], THR[60]]), axis=0)
CLI[59] = np.mean(np.stack([CLI[58], CLI[60]]), axis=0)
print("NaNs before smoothing: thr", np.isnan(THR).sum(), "cli", np.isnan(CLI).sum())

# wrap-around centred 31-day moving mean (d-15..d+15 mod 366)
def smooth31(A):  # A: (366, 60, 60)
    A3 = np.concatenate([A, A, A], axis=0)   # 3*366
    # S[d] = mean(A3[d+15-15 : d+15+16]) for d in 0..365 using window start index d (in middle copy)
    starts = np.arange(366) + 1              # window over A3[starts+d ... ] ; want A2[(d-15)..(d+15)]
    # simpler: pad = np.concatenate([A[351:], A, A[:15]])  -> window [d .. d+30]
    pad = np.concatenate([A[366-15:], A, A[:15]], axis=0)  # 366+30
    csum = np.nancumsum(pad, axis=0)
    cnt  = np.cumsum(np.isfinite(pad), axis=0)
    S = np.empty_like(A)
    for d in range(366):
        seg = csum[d+30] - (csum[d-1] if d > 0 else 0)
        n   = cnt[d+30] - (cnt[d-1] if d > 0 else 0)
        S[d] = seg / n
    return S

THR_s = smooth31(THR)
CLI_s = smooth31(CLI)
print("NaNs after smoothing: thr", np.isnan(THR_s).sum(), "cli", np.isnan(CLI_s).sum())
np.savez_compressed("/tmp/mhw/thrcli.npz", THR=THR_s, CLI=CLI_s)
print("thr range:", np.nanmin(THR_s)-273.15, np.nanmax(THR_s)-273.15, "degC")
