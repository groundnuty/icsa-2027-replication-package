import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
import datetime
def probe(d):
    p = f"{base}/sst_{d.strftime('%Y%m%d')}.nc"
    try:
        info = fs.info(p)
        return info['size']
    except Exception as e:
        return f"MISSING ({type(e).__name__})"
for d in [datetime.date(1991,12,27), datetime.date(2003,1,5), datetime.date(2016,6,1),
          datetime.date(2024,12,31), datetime.date(2025,1,1), datetime.date(2025,12,31),
          datetime.date(2026,1,1), datetime.date(2027,1,1)]:
    print(d, probe(d))
