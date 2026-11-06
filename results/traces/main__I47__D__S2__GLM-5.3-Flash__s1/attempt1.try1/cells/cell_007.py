import numpy as np
print('numpy', np.__version__)
nn = np.array([1.,2.,np.nan,4.])
r = np.nanquantile(nn, 0.9, method='hazen')
print('nanquantile hazen [1,2,nan,4] ->', repr(r))
print('quantile hazen [1,2,4] ->', repr(np.quantile(np.array([1.,2.,4.]), 0.9, method='hazen')))
print('nanquantile default ->', repr(np.nanquantile(nn, 0.9)))
try:
    print('positional method:', repr(np.nanquantile(nn, 0.9, None, False, 'hazen')))
except Exception as e:
    print('positional failed:', type(e).__name__, e)
# column-wise
M = np.array([[1.,2.,np.nan],[3.,np.nan,4.]])
print('col-wise:', np.nanquantile(M, 0.9, axis=0, method='hazen'))
