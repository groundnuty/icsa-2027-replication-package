import numpy as np, pickle, datetime as dt
D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
R = pickle.load(open("/tmp/mhw_results.pkl","rb"))
B, T = D["B"], D["T"]
Ths = R["Ths_h"]; tdoys = R["tdoys"]
tdays = D["tgt_dates"]

def show_cell(i, j):
    th = Ths[[ (i,j) for i2,j2 in [ (i,j) ]] ]
    # find cell index
    cells = np.argwhere(np.all(np.isfinite(T), axis=0))
    ci = int(np.where((cells[:,0]==i)&(cells[:,1]==j))[0][0])
    th = Ths[ci, tdoys-1]
    t = T[:, i, j]
    print("cell (i=%d j=%d)  day  sst   thr    diff" % (i, j))
    for k in range(92):
        d = tdays[k]
        if dt.date(2012,7,1) <= d <= dt.date(2012,7,20):
            print("  %s  %7.3f %7.3f %+8.4f %s" % (d, t[k], th[k], t[k]-th[k], "HOT" if t[k]>=th[k] else ""))

show_cell(1, 31)
show_cell(10, 2)