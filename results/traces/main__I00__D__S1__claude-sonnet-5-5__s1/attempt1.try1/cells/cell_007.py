import fsspec,pandas as pd,os
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/d',exist_ok=True)
need=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2004-06-01','2004-08-31'))
def g(d):
    n=f"sst_{d:%Y%m%d}.nc";l=f"/work/d/{n}"
    if os.path.exists(l):return None
    try: fs.get(f"{p}/{n}",l);return None
    except Exception as e:return (n,str(e)[:80])
with ThreadPoolExecutor(8) as ex: res=[r for r in ex.map(g,need) if r]
print(len(res),res[:5],len(os.listdir('/work/d')))