import numpy as np

def smooth366(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    cs  = np.concatenate([np.zeros((1,) + a.shape[1:]), np.cumsum(ext, axis=0)], axis=0)
    return (cs[31:] - cs[:-31]) / 31.0

a_test = np.arange(366, dtype=float)[:, None]
sm = smooth366(a_test)
print("shape", sm.shape)
print("sm[0]", sm[0,0], "expected", (np.arange(351,366).sum()+np.arange(0,15).sum())/31)
print("sm[150]", sm[150,0], "expected", np.arange(135,166).mean())
print("sm[365]", sm[365,0], "expected", (np.arange(350,366).sum()+np.arange(0,15).sum())/31)
# brute force check for all d
ok = True
for d in [0,1,14,15,16,150,350,365]:
    idx = (d-15+np.arange(31)) % 366
    e = a_test[idx,0].mean()
    if not np.allclose(sm[d,0], e):
        ok = False
        print("MISMATCH d", d, sm[d,0], e)
print("brute-force check:", "ok" if ok else "FAIL")
