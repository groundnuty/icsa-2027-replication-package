import numpy
import inspect, ast
f = numpy.lib._function_base_impl._compute_virtual_index
print(inspect.getsource(f))
print("-----")
# Just test the formula empirically against numpy
import numpy as np
rng = np.random.default_rng(3)
for n in [5,9,10,11,20,50]:
    x = np.sort(rng.normal(288,2,n))
    for q in [0.1,0.25,0.5,0.75,0.9,0.99]:
        r = np.quantile(x, q, method='hazen')
        # candidate A: v = n*q + 0.5 + 0.5*q - 1 = n*q + 0.5*q - 0.5
        vA = n*q + 0.5*q - 0.5
        vA = min(max(vA,0.0), n-1)
        j = int(np.floor(vA)); g = vA - j
        valA = x[j] + (g*(x[min(j+1,n-1)]-x[j]) if j+1<n else 0.0)
        # candidate B: v = n*q - 0.5
        vB = min(max(n*q-0.5,0.0), n-1)
        j = int(np.floor(vB)); g = vB - j
        valB = x[j] + (g*(x[min(j+1,n-1)]-x[j]) if j+1<n else 0.0)
        print(f"n={n} q={q}: numpy={r:.8f} A={valA:.8f}({'ok' if np.isclose(r,valA) else 'NO'}) B={valB:.8f}({'ok' if np.isclose(r,valB) else 'NO'})")
