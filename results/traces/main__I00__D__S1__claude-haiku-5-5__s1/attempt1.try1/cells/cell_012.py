s=open('/work/run.py').read().split("mhw=np.zeros")[0]
s += r'''
hotv=tgt[:,ys,xs]>=thr_s[tdoy][:,ys,xs]
print('hot fraction overall', hotv.mean(), 'max cell hot days', hotv.sum(0).max())
runs=[max([len(x) for x in ''.join('1' if v else '0' for v in hotv[:,c]).split('0')]) for c in range(len(ys))]
print('max consecutive hot run', max(runs))
print('SST target range', np.nanmin(tgt[:,ys,xs]), np.nanmax(tgt[:,ys,xs]))
print('thr sample', thr_s[[152,200,250]][:, ys[0], xs[0]], 'clim', clim_s[[152,200,250]][:,ys[0],xs[0]])
'''
exec(s)