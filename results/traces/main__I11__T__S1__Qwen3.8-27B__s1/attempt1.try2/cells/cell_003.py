
import fsspec
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'
# check if specific later files exist
for y in [1991, 1992, 2002, 2003, 2021]:
    import datetime
    for md in ["1227","0101","0601","0831"]:
        p = base + f"sst_{y}{md}.nc"
        try:
            attrs = fs.info(p)
            print(y, md, "EXISTS", attrs.get("size"))
        except Exception as e:
            print(y, md, "missing", type(e).__name__)
