path = '/work/pipeline.py'
src = open(path).read()
src = src.replace(
    "Xw = ds['analysed_sst'].isel(time=slice(t0b, t1b + 1), latitude=li, longitude=lo).values.astype(np.float64)\nT = Xw.shape[0]",
    "Xw = ds['analysed_sst'].isel(time=slice(t0b, t1b + 1), latitude=li, longitude=lo).values.astype(np.float64).reshape(-1, len(li)*len(lo))\nT = Xw.shape[0]")
src = src.replace(
    "Xt = ds['analysed_sst'].isel(time=slice(t0t, t1t + 1), latitude=li, longitude=lo).values.astype(np.float64)\nassert Xt.shape[0] == 92, Xt.shape",
    "Xt = ds['analysed_sst'].isel(time=slice(t0t, t1t + 1), latitude=li, longitude=lo).values.astype(np.float64).reshape(-1, len(li)*len(lo))\nassert Xt.shape[0] == 92, Xt.shape")
open(path, 'w').write(src)
import re
print([l for l in src.splitlines() if 'reshape' in l])
