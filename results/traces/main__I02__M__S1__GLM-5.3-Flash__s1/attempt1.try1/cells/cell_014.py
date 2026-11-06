import numpy as np
# corrected hazen: 1-based h = n*P + 0.5  -> 0-based pos = n*P - 0.5
def hazen_q90(pool, P=0.9):
    sv = np.sort(pool, axis=0)
    n = np.isfinite(pool).sum(axis=0)
    pos0 = n*P - 0.5
    lo0 = np.floor(pos0); hi0 = np.ceil(pos0)
    gamma = pos0 - lo0
    lo0 = np.clip(lo0, 0, None).astype(np.int64)
    hi0 = np.clip(hi0, 0, sv.shape[0]-1).astype(np.int64)
    r=np.arange(pool.shape[1])[:,None]; c=np.arange(pool.shape[2])[None,:]
    v_lo=sv[lo0,r,c]; v_hi=sv[hi0,r,c]
    out = v_lo + (v_hi-v_lo)*gamma
    out = np.where(gamma>=0.5, v_hi-(v_hi-v_lo)*(1.0-gamma), out)
    return np.where(n>0, out, np.nan)

rng=np.random.default_rng(1)
# scalar validation across sizes, incl. ties, NaNs
ok=True
for n in [1,2,3,4,5,7,10,11,17,50,101,121,366]:
    for trial in range(3):
        x=rng.random(n)
        if trial==1: x=np.round(x,1)  # ties
        if trial==2 and n>3: x[::3]=np.nan
        qn=np.nanquantile(x,0.9,method='hazen')
        col=x.reshape(-1,1,1)
        qm=hazen_q90(col)[0,0]
        if not (np.isclose(qn,qm,equal_nan=True)):
            ok=False; print("MISMATCH", n, trial, qn, qm)
print("scalar validation ok:", ok)

# random validation vs numpy nanquantile
pool=rng.random((121,6,6)); pool[rng.random(pool.shape)<0.1]=np.nan
qm=hazen_q90(pool)
with np.errstate(all='ignore'):
    qn=np.nanquantile(pool,0.9,axis=0,method='hazen')
d=np.abs(qm-qn); m=np.isfinite(d)
print("max|diff|:", d[m].max() if m.any() else 0.0, " nan pattern equal:", np.array_equal(np.isnan(qm),np.isnan(qn)))
# P=0.9 with n small integer cases: n=2: pos=1.3 -> between idx1 and 2? wait n=2: pos=2*0.9-0.5=1.3, clip hi to 1 -> x[1]. numpy: h=2*0.9+0.5=2.3 (1-based) -> clamp to x[2]?? check
x=np.array([1.0,2.0])
print("n=2:", np.nanquantile(x,0.9,method='hazen'), "mine:", hazen_q90(x.reshape(-1,1,1))[0,0])
x=np.array([1.0])
print("n=1:", np.nanquantile(x,0.9,method='hazen'), "mine:", hazen_q90(x.reshape(-1,1,1))[0,0])
