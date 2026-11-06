import numpy as np, pickle, warnings, os
with open('/tmp/stepA2.pkl','rb') as fh: A = pickle.load(fh)
mem = A['mem']; arr_sea = A['arr_sea']; thresh_s = A['thresh_s']; clim_s = A['clim_s']

def matlab_q(x, p=0.9):
    x = np.sort(x[np.isfinite(x)]); n = len(x)
    return float(np.interp(p, (np.arange(1, n+1)-0.5)/n, x))

# end-to-end: smoothed threshold & climatology at doy 183, cell 10, fully by hand (doy 168..198)
d = 183; cell = 10
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    q  = [matlab_q(arr_sea[mem[:, (i-1)]][:, cell]) for i in range(d-15, d+16)]   # doys 168..198
    mu = [float(np.nanmean(arr_sea[mem[:, (i-1)][:, None].ravel(), cell])) if False else float(np.nanmean(arr_sea[mem[:, i-1]][:, cell])) for i in range(d-15, d+16)]
print("thresh: hand %.10f vs saved %.10f  match=%s" % (np.mean(q), thresh_s[d-1, cell], np.isclose(np.mean(q), thresh_s[d-1, cell])))
print("clim:   hand %.10f vs saved %.10f  match=%s" % (np.mean(mu), clim_s[d-1, cell], np.isclose(np.mean(mu), clim_s[d-1, cell])))

# and the same at a wrap-around doy (doy 1 -> doys 352..366, 1..16)
d = 1
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    doys = [(d-15+k-1) % 366 + 1 for k in range(31)]
    q1 = [matlab_q(arr_sea[mem[:, i-1]][:, 500]) for i in doys]
print("doy1 wrap doys:", doys[0], "..", doys[14], ",", doys[15], "..", doys[-1])
print("thresh doy1: hand %.10f vs saved %.10f match=%s" % (np.mean(q1), thresh_s[0, 500], np.isclose(np.mean(q1), thresh_s[0, 500])))
