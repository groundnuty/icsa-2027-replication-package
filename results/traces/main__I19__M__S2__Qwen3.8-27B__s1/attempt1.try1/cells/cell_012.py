import numpy as np
import numpy.lib._function_base_impl as F
for name in ['hazen','weibull','linear','median_unbiased','normal_unbiased','interpolated_inverted_cdf','inverted_cdf','closest_observation','averaged_inverted_cdf']:
    M = F._QuantileMethods[name]
    f = M['get_virtual_index']; g = M['fix_gamma']
    rows = []
    for n, q in [(9, 0.9), (5, 0.9), (121, 0.9)]:
        try:
            h = f(n, q)
            hg = g(h, q) if g is not None else None
            rows.append((n, q, float(h), None if hg is None else float(hg)))
        except Exception as e:
            rows.append((n, q, "ERR", str(e)))
    print(f"{name:26s}", rows)
