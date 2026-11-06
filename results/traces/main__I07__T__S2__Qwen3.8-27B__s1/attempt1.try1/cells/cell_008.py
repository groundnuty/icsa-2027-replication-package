
import numpy as np, pandas as pd, os
for k in ['ext','tgt','ext_dates','tgt_dates','lat','lon']:
    p = f'/tmp/mhw/{k}.npy'
    a = np.load(p)
    print(k, a.shape, a.dtype, a.ravel()[:3] if a.dtype.kind in 'if' else '')
ed = np.load('/tmp/mhw/ext_dates.npy'); td = np.load('/tmp/mhw/tgt_dates.npy')
print("ext dates:", pd.Timestamp(ed[0]*10**9), "->", pd.Timestamp(ed[-1]*10**9), "n=", len(ed), "strictly daily:", bool((np.diff(ed)==1).all()))
print("tgt dates:", pd.Timestamp(td[0]*10**9), "->", pd.Timestamp(td[-1]*10**9), "n=", len(td), "strictly daily:", bool((np.diff(td)==1).all()))
lat = np.load('/tmp/mhw/lat.npy'); lon = np.load('/tmp/mhw/lon.npy')
print("lat:", lat[0], lat[-1], "lon:", lon[0], lon[-1])
print("np version:", np.__version__)
