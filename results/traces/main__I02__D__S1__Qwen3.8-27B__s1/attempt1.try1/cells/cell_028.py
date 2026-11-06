import numpy as np
# small case: n=10, p=0.9 -> h=(10+1)*0.9=9.9 -> 0.1*x_9 + 0.9*x_10
v = np.array([1.,2,3,4,5,6,7,8,9,10])
qn = np.quantile(v, 0.9, method='hazen')
print("numpy hazen n=10 p=0.9:", qn, "expected 9.9")
# n=121 check on ordered data
v = np.arange(1, 122, dtype=float)
qn = np.quantile(v, 0.9, method='hazen')
print("numpy hazen n=121 p=0.9:", qn, "expected 109.8")
# all methods for sanity
for m in ['linear','hazen','median_unbiased','inverted_cdf','nearest']:
    try:
        print(m, np.quantile(v, 0.9, method=m))
    except Exception as e:
        print(m, "ERR", e)
