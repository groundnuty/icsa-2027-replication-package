import numpy as np
print("numpy", np.__version__)
x = np.arange(1., 122.)
for p in (0.5, 0.25, 0.9, 0.1):
    print("p=%.2f" % p, "hazen=", np.quantile(x, p, method="hazen"),
          " linear=", np.quantile(x, p, method="linear"),
          " type5=(n-1)p+1 ->", (x.size-1)*p+1)
# so numpy hazen: h0_0based = n*p - 0.5 ? check p=0.25,n=121: 121*0.25-0.5=29.75 -> x[29]+0.75*(x[30]-x[29]) = 30.75
print("expected n*p-0.5:", 121*0.25-0.5)