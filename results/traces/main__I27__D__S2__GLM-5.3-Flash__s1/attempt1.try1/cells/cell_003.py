import numpy as np, os, sys, time
print('numpy', np.__version__)
print('cwd', os.getcwd())
# check hazen support
try:
    v = np.percentile(np.array([1.,2,3,4]), 90, method='hazen')
    print('hazen ok', v)
except Exception as e:
    print('hazen fail', e)
# hazen reference vs manual
a = np.array([1.,2,3,4,5])
print('p90 hazen', np.percentile(a,90,method='hazen'))
h = 0.9*5+0.5  # n*p+0.5
print('manual', a[int(np.floor(h))-1] if False else None)
