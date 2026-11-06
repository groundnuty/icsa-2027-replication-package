import fsspec, h5py, numpy as np, time, datetime as dt
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 404,463,559,618

# hazen check
rng = np.random.default_rng(0)
x = rng.normal(size=(137, 25))
x[0, 0] = np.nan
q_np = np.nanquantile(x, 0.9, axis=0, method='hazen')
def hazen_ref(a, q):  # manual type-5
    a = np.sort(np.asarray(a, dtype=np.float64))
    n = a.size
    h = q*(n+1) - 0.5  # p*(n+1)-... actually h = q*n + q - 0.5? use: h = q*(n+1) - 0.5
    lo = int(np.floor(h)) - 1; hi = min(lo+1, n-1); lo = max(lo, 0)
    g = h - (lo+1)
    return (1-g)*a[lo] + g*a[hi]
col = 3
print('hazen match:', np.isclose(q_np[col], hazen_ref(x[:, col], 0.9), atol=1e-12))

# benchmark 30 sequential reads spread over baseline
dates = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in (0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4027)]
t0=time.time(); nerr=0
for d in dates:
    try:
        with fs.open(f'{base}/sst_{d:%Y%m%d}.nc','rb') as f:
            with h5py.File(f,'r') as hf:
                ts = hf['time'][0]
                a = hf['analysed_sst'][0, i0:i1+1, j0:j1+1]
                decoded = (np.datetime64('1981-01-01') + np.timedelta64(int(ts),'s'))
                ok = str(decoded)[:10] == d.isoformat()
        if not ok: print('TIME MISMATCH', d, decoded)
    except Exception as e:
        nerr += 1; print('ERR', d, repr(e)[:80])
t1=time.time()
print('10 reads: %.2fs -> %.3fs/file, errors=%d' % (t1-t0, (t1-t0)/len(dates), nerr))
print('sample decoded', decoded, 'vs', d)
