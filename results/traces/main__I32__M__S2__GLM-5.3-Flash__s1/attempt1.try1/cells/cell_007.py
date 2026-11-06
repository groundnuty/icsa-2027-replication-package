import numpy as np, pickle, time, warnings
print("numpy", np.__version__)
import inspect
sig = inspect.signature(np.nanpercentile)
print("has method kwarg:", 'method' in sig.parameters)
with open("/tmp/data.pkl","rb") as f:
    D = pickle.load(data_file) if False else pickle.load(f)
data = D["data"]

# --- day-of-year mapping check ---
def doy_map(dates):
    d = dates.astype('datetime64[D]')
    y = d.astype('datetime64[Y]').astype(int) + 1970
    m = (d.astype('datetime64[M]') - d.astype('datetime64[Y]')).astype(int)  # 0..11
    def days_before_month(y, m0):
        cum = [0,31,59,90,120,151,181,212,243,273,304,334]
        n = cum[m0]
        if m0 >= 2 and (y%4==0 and (y%100!=0 or y%400==0)): n += 1
        return n
    dd = (d - d.astype('datetime64[M]') + np.timedelta64(1,'D')).astype(int)
    return np.array([days_before_month(yy, mm) + ddm for yy, mm, ddm in zip(y, m, dd)])

tests = ["1992-02-28","1992-02-29","1992-03-01","1993-02-28","1993-03-01","2000-12-31","2001-01-01","2005-06-01","2005-08-31","1996-12-31"]
for s in tests:
    print(s, "->", doy_map(np.array(np.datetime64(s), dtype='datetime64[D]'))[0] if doy_map(np.datetime64(s)).ndim else doy_map(np.datetime64(s)))
