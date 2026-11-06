import numpy as np, netCDF4
from datetime import date, timedelta

nc = netCDF4.Dataset('/work/data/sst_s2.nc', 'r')
a = nc['analysed_sst']
raw = np.asarray(nc['time'][:], dtype=np.float64)
epoch = date(1981,1,1)
days = np.round(raw/86400.0).astype(int)
dec_dates = np.array([epoch + timedelta(days=int(k)) for k in days])
def tidx(d):
    i = int(np.searchsorted(days, (d - epoch).days))
    assert dec_dates[i] == d
    return i
def dlist(y0,m0,d0_,y1,m1,d1):
    out, d = [], date(y0,m0,d0_)
    e = date(y1,m1,d1)
    while d <= e:
        out.append(d); d += timedelta(days=1)
    return out
ext = dlist(1991,12,27,2003,1,5)
base = dlist(1992,1,1,2002,12,31)
ext_idx = [tidx(d) for d in ext]

lat_all = nc['latitude'][:].astype(np.float64); lon_all = nc['longitude'][:].astype(np.float64)
lati = np.flatnonzero((lat_all >= 56.13) & (lat_all <= 57.33))
loni = np.flatnonzero((lon_all >= 17.71) & (lon_all <= 18.91))
nc.close()

si = np.load('/work/data/sea_idx.npy')
B = np.load('/work/data/B.npy')
c = 3299
r, cc = si[c]//60, si[c]%60
SITE_G, FC = int(lati[r]), int(loni[cc])
print("cell", c, "-> region", r, cc, "-> fullgrid", SITE_G, FC, "lat", lat_all[SITE_G], "lon", lon_all[FC])

# compare full 4028-day columns
import netCDF4 as n4
nc = n4.Dataset('/work/data/sst_s2.nc','r')
col_e = np.asarray(nc['analysed_sst'][ext_idx, SITE_G, FC], dtype=np.float64)
nc.close()
col_B = B[:, r, cc]
print("columns equal:", np.array_equal(col_e, col_B), "max diff:", np.abs(col_e-col_B).max())

# compare pools for doy 153
ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)
def doy_of(m, d):
    return d + (int(ENDS[m-2]) if m >= 2 else 0)
m, dd = md_of(153)
rows_ver = []
for b in base:
    if doy_of(b.month, b.day) == m*100+dd:
        j = ext.index(b)
        rows_ver.extend(range(j-5, j+6))
pool_ver = col_e[rows_ver]

d0 = date(1991,12,27)
rows_pipe = []
for y in range(1992, 2003):
    cc0 = date(y, m, dd)
    for k in range(-5, 6):
        rows_pipe.append((cc0 + timedelta(days=k) - d0).days)
pool_pipe = col_B[rows_pipe]
print("rows equal:", np.array_equal(np.array(rows_ver), np.array(rows_pipe)))
print("pools equal:", np.array_equal(pool_ver, pool_pipe))
# show first 12 of each
print("ver:", np.round(pool_ver[:12], 2))
print("pipe:", np.round(pool_pipe[:12], 2))