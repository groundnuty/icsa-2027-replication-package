import numpy as np, pickle
d = pickle.load(open('/work/step1.pkl','rb'))
thr_sm_full = pickle.load(open('/work/step2.pkl','rb'))  # keep thr_sm
thr_sm = thr_sm_full['thr_sm']
S_tgt, doy_tgt = d['S_tgt'], d['doy_tgt']
t_tgt = d['t_tgt']
S_tgt_c = S_tgt.reshape(-1, S_tgt.shape[0])
ncells = S_tgt_c.shape[0]; D = 92
sea = np.all(np.isfinite(S_tgt_c), axis=1)

hot = np.zeros_like(S_tgt_c, dtype=bool)
hot[sea] = S_tgt_c[sea] >= thr_sm[sea][:, doy_tgt]
print('hot day count:', int(hot.sum()))

def mhw_events_bruteforce(h):
    """Naive: maximal runs of >=5 hot days, merged over gaps of 1-2 non-hot days."""
    n = len(h)
    # find maximal hot runs
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = max(merged[-1][1], r[1])
        else:
            merged.append(list(r))
    return merged

# vectorized version (corrected length = ce - cs)
pad = np.zeros((ncells, D+2), dtype=bool); pad[:, 1:-1] = hot
rs, cs = np.nonzero(pad[:, 1:] & ~pad[:, :-1])
re, ce = np.nonzero(~pad[:, 1:] & pad[:, :-1])
assert len(rs) == len(re)
keep = (ce - cs) >= 5     # correct run length
rs, cs, ce = rs[keep], cs[keep], ce[keep]-1
events_vec = {}
cur = None
for i in range(len(rs)):
    c, s, e = int(rs[i]), int(cs[i]), int(ce[i])
    if cur is not None and cur[0] == c and s - cur[2] - 1 <= 2:
        cur = (c, cur[1], max(cur[2], e))
    else:
        if cur is not None: events_vec.setdefault(cur[0], []).append(tuple(cur[1:]))
        cur = (c, s, e)
if cur is not None: events_vec.setdefault(cur[0], []).append(tuple(cur[1:]))
print('qualifying runs:', int(len(rs)), 'events:', sum(len(v) for v in events_vec.values()), 'cells:', len(events_vec))

# brute-force check on all cells
mismatch = 0
checked = 0
for c in range(ncells):
    if not sea[c]:
        if c in events_vec: mismatch += 1
        continue
    bf = mhw_events_bruteforce(hot[c])
    vec = events_vec.get(c, [])
    checked += 1
    if bf != [list(x) for x in vec]:
        mismatch += 1
        if mismatch < 4:
            print('MISMATCH cell', c, 'bf', bf, 'vec', vec)
print('cells checked:', checked, 'mismatches:', mismatch)

lens = [e - s + 1 for v in events_vec.values() for s, e in v]
print('event lengths min/max:', min(lens), max(lens))
mhw = np.zeros((ncells, D), dtype=np.uint8)
for c, v in events_vec.items():
    for s, e in v:
        mhw[c, s:e+1] = 1
print('mhw ones:', int(mhw.sum()))
active = mhw.sum(axis=0) > 0
print('active days:', int(active.sum()))
ev = []
in_ev = False
for i in range(D):
    if active[i] and not in_ev:
        st = i; in_ev = True
    elif not active[i] and in_ev:
        ev.append((st, i-1)); in_ev = False
if in_ev: ev.append((st, D-1))
print('regional events:')
for s, e in ev:
    print('  ', str(t_tgt[s])[:10], '->', str(t_tgt[e])[:10], 'len', int(e - s + 1))
# days when few cells active (check for near-miss days)
per_day = mhw.sum(axis=0)
print('cells active per day (first 10):', per_day[:10])
print('min cells active on an active day:', int(per_day[active].min()))
pickle.dump(dict(mhw=mhw, events=ev, sea=sea, events_vec=events_vec), open('/work/step3.pkl','wb'))
print('saved step3')
