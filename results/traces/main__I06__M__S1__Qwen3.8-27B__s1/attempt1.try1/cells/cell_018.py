import numpy as np, datetime as dt, warnings
warnings.filterwarnings("ignore")

Z = np.load("/tmp/mhw/loaded.npz")
Vb, Vt = Z["Vb"], Z["Vt"]
BASE_START = dt.date(1991,12,27)
BL_START, BL_END = dt.date(1992,1,1), dt.date(2002,12,31)
leap_month = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
for m in range(1,13):
    s = 1
    for mm in range(1,m): s += leap_month[mm-1]
    for day in range(1, leap_month[m-1]+1):
        doy_of[(m,day)] = s + day - 1
bl_dates = [BL_START + dt.timedelta(days=i) for i in range((BL_END-BL_START).days+1)]
bl_ord = np.array([(dd.toordinal()-BASE_START.toordinal()) for dd in bl_dates])
bl_doy = np.array([doy_of[(dd.month,dd.day)] for dd in bl_dates])
pools = {d: np.unique(bl_ord[bl_doy==d][:,None] + np.arange(-5,6)[None,:]) for d in range(1,367) if d!=60}

THR = np.full((366, 60, 60), np.nan)
CLI = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    x = Vb[pools[d]]
    THR[d-1] = np.nanquantile(x, 0.90, method="hazen", axis=0)
    CLI[d-1] = np.nanmean(x, axis=0)
THR[59] = 0.5*(THR[58] + THR[60])
CLI[59] = 0.5*(CLI[58] + CLI[60])

sea = np.isfinite(Vt).all(axis=0)
print("pre-smooth NaN on sea cells: thr", int(np.isnan(THR[:,sea]).sum()), "cli", int(np.isnan(CLI[:,sea]).sum()))
print("pre-smooth NaN total: thr", int(np.isnan(THR).sum()), "(land cells:", int((np.isnan(THR).any(axis=0)).sum()), ")")

def smooth31(A):
    pad = np.concatenate([A[366-15:], A, A[:15]], axis=0)
    csum = np.nancumsum(pad, axis=0)
    cnt  = np.cumsum(np.isfinite(pad), axis=0)
    S = np.empty_like(A)
    for d in range(366):
        seg = csum[d+30] - (csum[d-1] if d > 0 else 0)
        n   = cnt[d+30]  - (cnt[d-1] if d > 0 else 0)
        S[d] = seg / n
    return S

THR_s = smooth31(THR); CLI_s = smooth31(CLI)
print("post-smooth NaN on sea cells: thr", int(np.isnan(THR_s[:,sea]).sum()), "cli", int(np.isnan(CLI_s[:,sea]).sum()))
np.savez_compressed("/tmp/mhw/thrcli.npz", THR=THR_s, CLI=CLI_s, THR0=THR, CLI0=CLI, sea=sea)
print("saved. thr(C) range:", np.nanmin(THR_s)-273.15, np.nanmax(THR_s)-273.15)
