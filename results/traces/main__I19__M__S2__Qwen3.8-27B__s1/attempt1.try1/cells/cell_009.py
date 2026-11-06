import numpy.lib._function_base_impl as F
import numpy as np
for name in ['hazen','weibull','linear','median_unbiased','normal_unbiased','interpolated_inverted_cdf']:
    f = F._QuantileMethods[name]['get_virtual_index']
    g = F._QuantileMethods[name]['fix_gamma']
    # probe behavior with n=9, q=0.9
    h = f(9, np.float64(0.9))
    hg = g(h) if g else None
    print(name, "h=", h, "fix_gamma=", hg)
