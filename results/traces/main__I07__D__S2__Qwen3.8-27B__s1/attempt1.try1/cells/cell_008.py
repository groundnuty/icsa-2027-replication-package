import numpy as np
# Test: 10 finite values 1..10 plus 3 NaNs
v = np.array([1.,2,3,4,5,6,7,8,9,10, np.nan, np.nan, np.nan])
n = 10
pos_manual = 1 + 0.9*(n-1)
print('manual hazen (n=finite=10): pos', pos_manual, '-> value', 1 + 0.9*(n-1))  # x[9] + 0.1*(x[10]-x[9]) = 9.1
print('numpy nanquantile:', np.nanquantile(v, 0.9, method='hazen'))
# also linear default
print('numpy nanquantile linear:', np.nanquantile(v, 0.9))
# what position does numpy use? If it used n=13: pos=1+0.9*12=11.8 -> between sorted[10] (NaN->?) and sorted[11]
# check docs behavior: does nanquantile count NaNs in n?
v2 = np.array([1.,2,3,4,5,6,7,8,9,10])
print('numpy quantile no-nan hazen:', np.quantile(v2, 0.9, method='hazen'))  # expect 9.1
# numpy 2.5 source check
import inspect, numpy.lib._nanfunctions_impl as nf
src = inspect.getsource(nf._nanquantile_1d) if hasattr(nf, '_nanquantile_1d') else None
print(src[:3000] if src else 'no _nanquantile_1d')
