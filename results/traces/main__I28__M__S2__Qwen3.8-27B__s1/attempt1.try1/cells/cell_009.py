import numpy as np

def hf_type5_quantile(x, p):
    """Hyndman-Fan type 5: p_k = (k-0.5)/(n+1), linear interp in p through (p_k, x_k)."""
    x = np.sort(np.asarray(x, float))
    n = len(x)
    # 1-indexed virtual position
    h1 = (n + 1) * p + 0.5
    # clamp to [1, n]
    h1 = min(max(h1, 1.0), float(n))
    i = int(np.floor(h1))
    frac = h1 - i
    if i >= n:
        return x[n-1]
    return x[i-1] + frac * (x[i] - x[i-1])

def hf_type5_from_paper(x, p):
    """HF(1996) inversion: h(p) = (n+1)p - k with k=0.5, 0-indexed interpolation."""
    x = np.sort(np.asarray(x, float))
    n = len(x)
    h0 = (n + 1) * p - 0.5   # 0-indexed
    h0 = min(max(h0, 0.0), float(n - 1))
    i = int(np.floor(h0)); frac = h0 - i
    if i >= n - 1: return x[n-1]
    return x[i] + frac * (x[i+1] - x[i])

rng = np.random.default_rng(0)
x = rng.standard_normal(121)
print("numpy hazen   :", np.quantile(x, 0.9, method="hazen"))
print("HF5 (interp)  :", hf_type5_quantile(x, 0.9))
print("HF5 (paper h0):", hf_type5_from_paper(x, 0.9))
print("numpy linear  :", np.quantile(x, 0.9, method="linear"))
print("numpy weibull :", np.quantile(x, 0.9, method="weibull"))
print("numpy midpoint:", np.quantile(x, 0.9, method="midpoint"))
print("numpy nearest :", np.quantile(x, 0.9, method="nearest"))
print("numpy higher  :", np.quantile(x, 0.9, method="higher"))
print("numpy lower   :", np.quantile(x, 0.9, method="lower"))

# small array hand-check
xs = np.array([1.0,2,3,4])
for m in ["hazen","linear","weibull","median_unbiased","nearest"]:
    try:
        print("x=[1,2,3,4] p=0.9", m, np.quantile(xs, 0.9, method=m))
    except Exception as e:
        print(m, "err", e)
print("HF5 x=[1,2,3,4] p=0.9:", hf_type5_quantile(xs, 0.9))
print("HF5 x=[1,2,3,4] p=0.3:", hf_type5_quantile(xs, 0.3))
print("numpy hazen x=[1,2,3,4] p=0.3:", np.quantile(xs, 0.3, method="hazen"))
