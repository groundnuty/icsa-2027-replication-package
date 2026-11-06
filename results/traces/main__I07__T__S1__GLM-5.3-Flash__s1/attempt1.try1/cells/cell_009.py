import fsspec, numpy as np, datetime as dt, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Build required date list
def dates_range(a,b):
    d = a; out=[]
    while d<=b: out.append(d); d+=dt.timedelta(days=1)
    return out
need = dates_range(dt.date(1991,12,27), dt.date(2003,1,5)) + dates_range(dt.date(2021,6,1), dt.date(2021,8,31))
print("total needed:", len(need))

missing = []
t0=time.time()
for d in need:
    p = f"{base}/sst_{d:%Y%m%d}.nc"
    ok=False
    for attempt in range(3):
        try:
            fs.info(p); ok=True; break
        except Exception as ex:
            if attempt==2: missing.append((str(d), str(ex)[:80]))
            time.sleep(0.5)
    if not ok: pass
print("check time:", round(time.time()-t0,1), "s; missing:", missing)
