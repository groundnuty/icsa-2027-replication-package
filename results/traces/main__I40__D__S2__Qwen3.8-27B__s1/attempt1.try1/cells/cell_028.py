import h5py, numpy as np, datetime
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
la = np.asarray(f['latitude']); lo = np.asarray(f['longitude'])
E0 = datetime.date(1982,1,1)
def i_of(d): return (d - E0).days
il = np.arange(404, 464); io = np.arange(559, 619)
for d in [datetime.date(1992,1,1), datetime.date(1996,7,1), datetime.date(2000,1,1),
          datetime.date(2009,6,1), datetime.date(2009,7,15), datetime.date(2009,8,31),
          datetime.date(1995,1,15), datetime.date(2001,1,15), datetime.date(2002,7,1),
          datetime.date(1991,12,27), datetime.date(2003,1,5)]:
    a = v[i_of(d)][il, io]
    fin = a[np.isfinite(a)]
    print(d, "finite:", fin.size, "of", a.size,
          ("min %.2f max %.2f med %.2f" % (fin.min(), fin.max(), np.median(fin))) if fin.size else "")
# 2D map for 2009-07-15
a = v[i_of(datetime.date(2009,7,15))][il, io]
np.set_printoptions(linewidth=250, precision=2)
print(a)
f.close()
