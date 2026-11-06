import numpy as np
x = np.array([1.,2,3,4,5])
for meth in ['hazen','linear']:
    print(meth, np.quantile(x, 0.3, method=meth), np.quantile(x, 0.9, method=meth))
# type 5: h=(n+1)p. n=5,p=0.3 -> h=1.8 -> 0.2*1+0.8*2 = 1.8
# type 7: h=(n-1)p+1 = 2.2 -> 0.8*1+0.2*2 = 1.2
print("expected type5 p=0.3: 1.8, type7: 1.2")
print("expected type5 p=0.9: h=5.4 -> clamp to 5? or interpolate beyond? HF says q=x_n when h>n")
# now with a 121-point vector, compare np.quantile hazen vs manual
rng = np.random.default_rng(42)
v = rng.normal(280, 5, 121)
vs = np.sort(v)
h = 122*0.9
j = int(np.floor(h)); g = h-j
manual = (1-g)*vs[j-1] + g*vs[j]
print("manual:", manual, "np hazen:", np.quantile(v, 0.9, method='hazen'))
print("positions:", vs[j-1], vs[j], "h=",h)
