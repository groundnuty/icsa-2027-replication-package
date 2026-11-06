import numpy as np, os

mask = np.load('/work/mask.npy')
tgt = np.load('/work/tgt.npy'); thr = np.load('/work/thr.npy'); sea = np.load('/work/sea_mask.npy')
nt, ncells = mask.shape
print("cwd:", os.getcwd())
print("mask dtype/shape:", mask.dtype, mask.shape, "values:", np.unique(mask))
print("mask nonzero on land cells:", int(mask[:, ~sea].sum()))
hot = np.zeros_like(mask, dtype=bool)
doy = np.arange(153, 245)
hot[:, sea] = tgt[:, sea] >= thr[doy-1][:, sea]

# reconstruct spans from mask and verify properties per cell
import itertools
def spans_from_mask(col):
    idx = np.where(col)[0]
    if not len(idx): return []
    out = []
    for s in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
        out.append((int(s[0]), int(s[-1])))
    return out

bad = 0
for c in range(ncells):
    sp = spans_from_mask(mask[:, c])
    if not sp: continue
    for (s, e) in sp:
        days = np.arange(s, e+1)
        h = hot[days, c]
        # property 1: every position in span covered by a >=5 hot run or a gap<=2 bridge
        # check: first hot run within span has length >=5, and hot runs in span:
        idx = np.where(h)[0]
        segs = []
        if len(idx):
            for i in range(len(idx)):
                if i+1 < len(idx) and idx[i+1]-idx[i] > 1: segs.append(idx[:i+1])
            segs.append(idx[i:])
        # all internal hot segments must be >=5? No: bridging hot segments shorter than 5 can exist inside a merged span
        # Real properties: (a) span starts at a hot day, ends at a hot day; (b) there exists a >=5 hot run inside;
        # (c) gap between consecutive hot segments inside span <= 2
        if not h[0] or not h[-1]: bad += 1; print("span not hot at ends", c, s, e); break
        if len(segs) < 1: bad += 1; break
        if max(len(g) for g in segs) < 5: bad += 1; print("no >=5 run", c, s, e); break
        for i in range(len(segs)-1):
            gap = segs[i+1][0] - segs[i][-1] - 1
            if gap > 2: bad += 1; print("gap>2", c, s, e, gap); break
print("structural violations:", bad)

# verify no mask day lies outside a valid merged MHW: recompute spans independently
def cell_mhw_runs(h):
    idx = np.where(h)[0]
    runs = []
    if len(idx):
        for s in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
            if len(s) >= 5: runs.append([int(s[0]), int(s[-1])])
    joined = []
    for r in runs:
        if joined and r[0] - joined[-1][1] - 1 <= 2: joined[-1][1] = r[1]
        else: joined.append(list(r))
    return [tuple(x) for x in joined]

bad2 = 0
for c in range(ncells):
    expect = np.zeros(nt, bool)
    for (s, e) in cell_mhw_runs(hot[:, c]):
        expect[s:e+1] = True
    if not np.array_equal(mask[:, c], expect.astype(np.uint8)):
        bad2 += 1
print("cells where mask != recomputation:", bad2)

# summary stats
print("per-day active count:", mask.sum(axis=1).astype(int).tolist())
