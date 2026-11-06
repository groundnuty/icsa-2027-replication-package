import numpy as np, datetime as dtm, time

# --- day-of-year mapping check (1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, 31 Dec=366) ---
cum = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
def doy_arr(dates):  # dates: datetime64[D]
    months = dates.astype('datetime64[M]')
    m = (months - months.astype('datetime64[Y]')).astype(int) + 1
    day = (dates - months).astype(int) + 1
    years = dates.astype('datetime64[Y]').astype(int) + 1970
    leap = (years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))
    yday = cum[m-1] + day
    return np.where(~leap & (yday >= 60), yday + 1, yday)

tests = {'2009-06-01':153, '2009-08-31':244, '1992-02-29':60, '1993-02-28':59,
         '1993-03-01':61, '2000-12-31':366, '1993-12-31':366, '2009-01-01':1}
for s, exp in tests.items():
    got = int(doy_arr(np.array(np.datetime64(s))))
    print(s, got, 'OK' if got==exp else f'MISMATCH exp {exp}')

# --- hazen quantile check vs manual (type 5: h = p*(n+1) - ... check) ---
rng = np.random.default_rng(0)
x = rng.normal(size=37)
n = len(x)
xs = np.sort(x)
for p in (0.25, 0.5, 0.9):
    h = (n+1)*p  # candidate? numpy hazen def
    print('p', p, 'numpy hazen:', np.percentile(x, p*100, method='hazen'),
          'h=(n+1)p interp:', np.interp((n+1)*p, np.arange(1, n+1), xs),
          'h=pn+0.5 interp:', np.interp(n*p+0.5, np.arange(1, n+1), xs))

# --- timing of nanpercentile hazen on pool-sized array ---
V = rng.normal(size=(121, 3600))
V[::10] = np.nan
t0 = time.time()
r = np.nanpercentile(V, 90, axis=0, method='hazen')
t1 = time.time()
print('nanpercentile 121x3600:', round(t1-t0, 4), 's')
t0 = time.time()
m_ = np.nanmean(V, axis=0)
t1 = time.time()
print('nanmean:', round(t1-t0, 4), 's')