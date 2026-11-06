import numpy as np, json
from datetime import date, timedelta
st = np.load('/tmp/mhw_state.npz')
Tf, thr, clim, thr_s, clim_s, hot, cellmhw, sea = st['Tf'], st['thr'], st['clim'], st['thr_s'], st['clim_s'], st['hot'], st['cellmhw'], st['sea']
leap = date(2000,1,1)
cal2doy = {( (leap+timedelta(days=d-1)).month, (leap+timedelta(days=d-1)).day ): d for d in range(1,367)}
t_tdates = [date(2014,6,1)+timedelta(days=k) for k in range(Tf.shape[0])]
t_doy = [cal2doy[(d.month, d.day)] for d in t_tdates]

# day60 fill on sea cells
print('day60 fill (sea):', np.allclose(thr[59, sea], 0.5*(thr[58, sea]+thr[60, sea])),
      np.allclose(clim[59, sea], 0.5*(clim[58, sea]+clim[60, sea])))
# smooth check on sea cells
ok = True
for d in [1, 2, 60, 61, 153, 244, 351, 365, 366]:
    rows = [(d-1-15+j) % 366 for j in range(31)]
    ok &= np.allclose(thr_s[d-1, sea], thr[rows][:, sea].mean(axis=0))
    ok &= np.allclose(clim_s[d-1, sea], clim[rows][:, sea].mean(axis=0))
print('SMOOTH CHECK (sea):', ok)

# alt interpretation: merge if count of NON-HOT days strictly between two consecutive candidates <= 2
cm_alt = np.zeros(Tf.shape, dtype=bool)
n_alt_extra = 0
for c in range(Tf.shape[1]):
    h = hot[:, c]
    p = np.concatenate(([False], h, [False])); d1 = np.diff(p.astype(np.int8))
    s = np.where(d1==1)[0]; e = np.where(d1==-1)[0]-1
    cands = [(s_, e_) for s_, e_ in zip(s, e) if e_-s_+1 >= 5]
    merged = []
    for s_, e_ in cands:
        if merged:
            prev_e = merged[-1][1]
            between = e_ - prev_e - 1
            nonhot = between - int(h[prev_e+1:e_].sum())
            if nonhot <= 2:
                merged[-1] = (merged[-1][0], e_)
            else:
                merged.append((s_, e_))
        else:
            merged.append((s_, e_))
    for s_, e_ in merged:
        cm_alt[s_:e_+1, c] = True
    n_extra = int(cm_alt[:, c].sum()) - int(cellmhw[:, c].sum())
    n_alt_extra += max(n_extra, 0)
diff = (cm_alt != cellmhw)
print('cells affected by alt interpretation:', int(diff.any(axis=0).sum()), 'extra MHW-days total:', n_alt_extra)
act_alt = cm_alt.any(axis=1)
pa = np.concatenate(([False], act_alt, [False])); da = np.diff(pa.astype(np.int8))
es = np.where(da==1)[0]; ee = np.where(da==-1)[0]-1
ev_alt = [(str(t_tdates[s_].isoformat()), str(t_tdates[e_].isoformat())) for s_, e_ in zip(es, ee)]
act = cellmhw.any(axis=1)
pa = np.concatenate(([False], act, [False])); da = np.diff(pa.astype(np.int8))
es = np.where(da==1)[0]; ee = np.where(da==-1)[0]-1
ev = [(str(t_tdates[s_].isoformat()), str(t_tdates[e_].isoformat())) for s_, e_ in zip(es, ee)]
print('events (mine):', json.dumps(ev))
print('events (alt) :', json.dumps(ev_alt))
print('active days mine/alt:', int(act.sum()), int(act_alt.sum()))
# where do they differ?
print('diff days:', [str(t_tdates[i].isoformat()) for i in np.where(act != act_alt)[0]])
# for the differing cells: show structure of one example
cex = np.where(diff.any(axis=0))[0][0]
h = hot[:, cex]
p = np.concatenate(([False], h, [False])); d1 = np.diff(p.astype(np.int8))
s = np.where(d1==1)[0]; e = np.where(d1==-1)[0]-1
print('example cell', cex, 'runs:', [(str(t_tdates[s_].isoformat()), str(t_tdates[e_].isoformat()), e_-s_+1) for s_,e_ in zip(s,e)])
