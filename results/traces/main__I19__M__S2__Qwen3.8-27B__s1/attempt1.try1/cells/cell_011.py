import numpy as np
import numpy.lib._function_base_impl as F
# probe the lambda signatures
for name in ['hazen','weibull','linear','median_unbiased','normal_unbiased','interpolated_inverted_cdf']:
    M = F._QuantileMethods[name]
    f = M['get_virtual_index']; g = M['fix_gamma']
    out = []
    for n, q in [(9, 0.9), (5, 0.9), (121, 0.9)]:
        try:
            h = f(n, np.float64(q), 0)
            hg = g(h, np.float64(q), 0) if g is not None else None
            out.append((n, q, float(h), None if hg is None else float(hg)))
        except Exception as e:
            out.append((n, q, "ERR", str(e)))
    print(name, out)
