import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check specific files exist
import datetime as dt
def name(y,m,d): return f"{y:04d}{m:02d}{d:02d}"
tests = [
 ("1991-12-27", dt.date(1991,12,27)),
 ("1991-12-31", dt.date(1991,12,31)),
 ("1992-01-01", dt.date(1992,1,1)),
 ("2003-01-05", dt.date(2003,1,5)),
 ("2002-12-31", dt.date(2002,12,31)),
 ("2009-06-01", dt.date(2009,6,1)),
 ("2009-08-31", dt.date(2009,8,31)),
]
for label, d in tests:
    p = f"{base}/sst_{name(*d.timetuple()[:3])}.nc"
    try:
        info = fs.info(p)
        print(label, info.get('size'), p)
    except Exception as e:
        print(label, "ERR", type(e).__name__, e)
