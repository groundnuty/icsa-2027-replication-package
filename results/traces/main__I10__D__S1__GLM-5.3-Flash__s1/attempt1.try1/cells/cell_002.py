import fsspec, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check which years are present via glob
for y in [1991, 1992, 2002, 2003, 2005, 2006, 2010, 2020, 2024, 2025]:
    try:
        g = fs.glob(f'{base}/sst_{y}0101.nc')
        print(y, 'Jan1 exists:', bool(g))
    except Exception as e:
        print(y, 'glob ERR', repr(e))

# count files in a year
try:
    g92 = fs.glob(f'{base}/sst_1992*.nc')
    print('1992 files:', len(g92))
    g05 = fs.glob(f'{base}/sst_2005*.nc')
    print('2005 files:', len(g05), g05[:3], g05[-3:])
except Exception as e:
    print('count ERR', repr(e))
