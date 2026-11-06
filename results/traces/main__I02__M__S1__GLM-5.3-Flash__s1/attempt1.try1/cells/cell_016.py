import numpy as np
def hazen_q90(pool, P=0.9):
    sv = np.sort(pool, axis=0)
    n = np.isfinite(pool).sum(axis=0)
    pos0 = n*P - 0.5
    lo0 = np.floor(pos0); hi0 = np.ceil(pos0)
    gamma = pos0 - lo0
    nclip = np.maximum(n-1, 0)  # if n==0, clip to 0; masked later (that column all-NaN)
    lo0 = np.clip(lo0, 0, None); hi0 = np.clip(hi0, 0, None)
    lo0 = np.minimum(lo0, nclip).astype(np.int64)
    hi0 = np.minimum(hi0, nclip).astype(np.int64)
    r=np.arange(pool.shape[1])[:,None]; c=np.arange(pool.shape[2])[None,:]
    v_lo=sv[lo0,r,c]; v_hi=sv[hi0,r,c]
    out = v_lo + (v_hi-v_lo)*gamma
    out = np.where(gamma>=0.5, v_hi-(v_hi-v_lo)*(1.0-gamma), out)
    return np.where(n>0, out, np.nan), n

rng=np.random.default_rng(1)
ok=True
for n in [1,2,3,4,5,6,7,10,11,17,50,101,121,366]:
    for trial in range(4):
        x=rng.random(n)
        if trial==1: x=np.round(x,1)
        if trial==2 and n>2: x[::3]=np.nan
        if trial==3 and n>4: x[:]=np.nan
        qn=np.nanquantile(x,0.9,method='hazen')
        qm,_=hazen_q90(x.reshape(-1,1,1)); qm=qm[0,0]
        if not (np.isclose(qn,qm,equal_nan=True) or (np.isnan(qn) and np.isnan(qm))):
            ok=False; print("MISMATCH", n, trial, qn, qm)
print("scalar validation ok:", ok)
for n in [2,3,5,11]:
    pool=rng.random((20,n,n)); pool[rng.random(pool.shape)<0.6]=np.nan
    qm,_=hazen_q90(pool)
    with np.errstate(all='ignore'):
        qn=np.nanquantile(pool,0.9,axis=0,method='hazen')
    d=np.abs(qm-qn); m=np.isfinite(d)
    print(n, "max|diff|:", d[m].max() if m.any() else 0.0, "nan equal:", np.array_equal(np.isnan(qm),np.isnan(qn)))
pool=np.full((7,2,2), np.nan); pool[:,1,1]=rng.random(7)
qm,_=hazen_q90(pool)
with np.errstate(all='ignore'):
    qn=np.nanquantile(pool,0.9,axis=0,method='hazen')
print("all-nan col:", qm[0,0], qn[0,0], " other:", qm[1,1], qn[1,1])
