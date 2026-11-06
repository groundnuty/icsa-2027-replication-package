import numpy as np, datetime as dt
TC = np.load("/tmp/mhw/thrcli.npz"); THR = TC["THR"]; sea = TC["sea"]
Z = np.load("/tmp/mhw/loaded.npz"); Vt = Z["Vt"]
TG_START = dt.date(2012,6,1)
tgt_dates = [TG_START + dt.timedelta(days=i) for i in range(92)]
leap_month = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
for m in range(1,13):
    s = 1
    for mm in range(1,m): s += leap_month[mm-1]
    for day in range(1, leap_month[m-1]+1): doy_of[(m,day)] = s + day - 1

def show(r, c, dates):
    print(f"cell ({r},{c}) lat~{54.46+0.02*r:.2f} lon~{16.06+0.02*c:.2f}")
    for dd in dates:
        i = (dd - TG_START).days
        d = doy_of[(dd.month, dd.day)]
        s, t = Vt[i,r,c], THR[d-1,r,c]
        print(f"  {dd.isoformat()} doy={d} SST={s:.4f} K thr={t:.4f} K hot={s>=t} margin={s-t:+.4f}")

show(10,27, [dt.date(2012,6,9), dt.date(2012,6,10), dt.date(2012,6,11), dt.date(2012,6,16), dt.date(2012,6,17), dt.date(2012,6,18)])
show(9,27, [dt.date(2012,6,10), dt.date(2012,6,11), dt.date(2012,6,16), dt.date(2012,6,17)])
show(15,55, [dt.date(2012,7,24), dt.date(2012,7,25), dt.date(2012,7,29), dt.date(2012,7,30)])
show(11,39, [dt.date(2012,6,10), dt.date(2012,6,11), dt.date(2012,6,16), dt.date(2012,6,17)])
