import numpy as np
x = np.arange(1.0, 10.0)  # 1..9
for m in ["inverted_cdf","averaged_inverted_cdf","closest_observation","interpolated_inverted_cdf","hazen","weibull","median_unbiased","normal_unbiased","linear"]:
    try:
        print(m, np.quantile(x, 0.9, method=m))
    except Exception as e:
        print(m, "ERR", e)
# expected HF type4 (hazen): h=(n+1)q-0.5=8.5 -> 8.5
# HF type5 (median-unbiased approx): (n+0.25)q-0.25 = 8.075
# HF type6 (normal/logistic-unbiased k/(n+1)): h=(n+1)q=9 -> 9? (clamped)
# HF type7 linear: (n-1)q+1 = 8.2 -> 8.2
import inspect, numpy.lib._function_base_impl as F
src = inspect.getsource(F._quantile_onesample)
print(src[:3000])
