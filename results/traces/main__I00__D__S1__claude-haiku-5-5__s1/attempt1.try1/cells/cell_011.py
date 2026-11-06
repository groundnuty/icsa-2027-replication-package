s=open('/work/run.py').read().split("ys,xs=np.where(sea)")[0]
exec_code = s + r'''
hotv=tgt[:,ys,xs]>=thr_s[tdoy][:,ys,xs]
print('hot fraction overall', hotv.mean(), 'max cell hot days', hotv.sum(0).max())
print('max consecutive hot run', max(
  max([len(x) for x in ''.join('1' if v else '0' for v in hotv[:,c]).split('0')]) for c in range(0,len(ys),50)))
print('SST target range', np.nanmin(tgt[:,ys,xs]), np.nanmax(tgt[:,ys,xs]))
print('thr sample', thr_s[[152,200,250]][:, ys[0], xs[0]], 'clim', clim_s[[152,200,250]][:,ys[0],xs[0]])
'''
exec(exec_code)