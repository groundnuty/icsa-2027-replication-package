import numpy as np
a = np.arange(1, 122, dtype=float)
for m in ["inverted_cdf","averaged_inverted_cdf","closest_observation","interpolated_inverted_cdf",
          "hazen","weibull","median_unbiased","normal_unbiased","linear"]:
    try:
        print(m, np.quantile(a, 0.9, method=m))
    except Exception as e:
        print(m, "ERR", e)
# Manual HF type 5 (median-unbiased): h = n*p + 1 (1-based)
n, p = 121, 0.9
for name, h in [("HF type2 hazen h=(n+1)p-1/2", (n+1)*p-0.5),
                ("HF type5 h=np+1", n*p+1),
                ("HF type6 h=(n+.35)p+.65", (n+0.35)*p+0.65),
                ("HF type7 h=(n-1)p+1", (n-1)*p+1)]:
    j = int(np.floor(h)); g = h - j
    print(name, h, "->", a[j-1] + g*(a[j]-a[j-1]))
