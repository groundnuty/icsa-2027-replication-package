import numpy as np
import numpy.lib._function_base_impl as F

# probe hazen virtual index formula
f = F._QuantileMethods['hazen']['get_virtual_index']
g = F._QuantileMethods['hazen']['fix_gamma']
print("probing hazen h0(n,q):")
for n in [5, 9, 121]:
    for q in [0.5, 0.9, 0.95]:
        print(n, q, f(n, q), "->", g(f(n, q), q))

# NaN handling check: column with NaNs
a = np.array([1.0, 2.0, np.nan, 4.0, 6.0, 8.0])
print("nanquantile hazen:", np.nanquantile(a, 0.9, method='hazen'), " n=5 -> expect h0=(6*0.9-1.4)=4.0 -> 8.0")
a2 = np.array([1.0, 2.0, np.nan, np.nan, 6.0, 8.0])
print("n=4:", np.nanquantile(a2, 0.9, method='hazen'), " h0=(5*0.9-1.4)=3.1 -> 6+0.1*2=6.2")
