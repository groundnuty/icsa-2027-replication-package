import numpy as np, inspect
import numpy.lib._function_base_impl as fb
src = inspect.getsource(fb)
i = src.find('def _compute_virtual_index')
print(src[i:i+700])
# numeric checks against a manual formula: virtual index v = n*q + 0.5 - 1? or (n-1)q + 0.5?
for arr, p in [
    (list(range(1,12)), 0.9),          # n=11 -> numpy gave 10.4
    (list(range(1,5)), 0.25),
    (list(range(1,5)), 0.75),
]:
    a = np.array(arr, dtype=float)
    n = len(a)
    q = np.array([p])
    for formula_name, v in [
        ("n*q+m-1, m=.5", n*p + 0.5 - 1),
        ("(n-1)q+m, m=.5", (n-1)*p + 0.5),
    ]:
        j = int(np.floor(v)); g = v - j
        # numpy virtual index is 1-based? Let's just compare both interpretations
        # interp 0-based with v-1 offset
        v0 = v - 1
        j0 = int(np.floor(v0)); g0 = v0 - j0
        v0c = np.clip(v0, 0, n-1)
        res = (1-g0)*a[j0] + g0*a[min(j0+1, n-1)]
        print(arr, p, formula_name, "np:", np.quantile(a, p, method='hazen'), "interp0based:", res)
