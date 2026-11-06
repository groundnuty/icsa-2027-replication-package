s=open('/work/run.py').read().split("mhw=np.zeros")[0]
s += r'''
anom = tgt[:,ys,xs]-thr_s[tdoy][:,ys,xs]
print('mean anomaly vs thr by month', [float(anom[i:i+30].mean()) for i in (0,30,60)])
print('median SST by day sample', np.median(tgt[::15][:,ys,xs],axis=1))
print('thr by doy at cell, doy 152..160', thr_s[152:161,ys[0],xs[0]])
print('clim vs thr check', np.nanmean(thr_s[1:]-clim_s[1:]))
'''
exec(s)