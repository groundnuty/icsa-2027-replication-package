import numpy as np, warnings
warnings.filterwarnings('ignore')
code=open('/tmp/analysis.py').read().split('# per-cell MHW')[0]
g={}
exec(code,g)
T=g['T'];th=g['th'];sea=g['sea']
print(np.nanmin(th[:,sea]),np.nanmax(th[:,sea]), np.isnan(th[:,sea]).sum())
diff=(T-th)[:,sea]
print('max T-th',np.nanmax(diff),'count >=0',np.sum(diff>=0), 'T range',np.nanmin(T[:,sea]),np.nanmax(T[:,sea]))
print('thr sample',th[:,sea][ipv6-20,0])