import numpy as np, datetime as dt, h5py
D='/data/icsa2027_data_20261101T090944Z/s1z'
def dval(y,m,d,i=40,j=40):
    with h5py.File(f'{D}/sst_{y}{m:02d}{d:02d}.nc','r') as f:
        return float(f['analysed_sst'][0,i,j])
for md in [(8,1),(6,1),(2,28)]:
    donors=[dt.date(y,*md) for y in range(1992,2003)]
    dates=set()
    for dd in donors:
        for k in range(-5,6): dates.add(dd+dt.timedelta(days=k))
    dates=sorted(dates)
    vals=np.array([dval(x.year,x.month,x.day) for x in dates])
    print(md, "n_dates:", len(dates), "n_nan:", int(np.isnan(vals).sum()), "sample:", vals[:6].round(2))
