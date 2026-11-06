import numpy as np
# reproduce: what does nanquantile hazen do on an empty pool?
try:
    x = np.empty((0, 4))
    np.nanquantile(x, 0.9, axis=0, method='hazen')
    print('empty ok')
except Exception as e:
    print('empty err:', type(e).__name__, e)
# normal case
rng = np.random.default_rng(0)
x = rng.random((121, 4))
print('normal:', np.nanquantile(x, 0.9, axis=0, method='hazen'))
with_nan = x.copy(); with_nan[3,2] = np.nan
print('with nan:', np.nanquantile(with_nan, 0.9, axis=0, method='hazen'))
allnan = np.full((5, 4), np.nan)
try:
    print(np.nanquantile(allnan, 0.9, axis=0, method='hazen'))
except Exception as e:
    print('allnan err:', type(e).__name__, e)
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    print('allnan supressed:', np.nanquantile(allnan, 0.9, axis=0, method='hazen'))
