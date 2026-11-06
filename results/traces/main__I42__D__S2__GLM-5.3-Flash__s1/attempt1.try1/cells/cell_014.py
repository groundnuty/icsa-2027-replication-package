import numpy as np, pandas as pd

z = np.load('/work/final.npz')
hot, sea, per_cell = z['hot'], z['sea'], z['per_cell']
tgt_dates = pd.read_pickle('/work/tgt_dates.pkl')
nd = len(tgt_dates)
ds_ = [d.date().isoformat() for d in tgt_dates]

def find_runs(f, minlen):
    runs=[]; n=len(f); i=0
    while i < n:
        if f[i]:
            j=i
            while j+1<n and f[j+1]: j+=1
            if j-i+1>=minlen: runs.append([i,j])
            i=j+1
        else: i+=1
    return runs

# distribution of ALL hot-run lengths (sea cells)
lens = {}
cells_with_events = {}
n_per_cell_events = 0
event_times = []
for ci in range(60):
    for cj in range(60):
        if not sea[ci,cj]: continue
        runs = find_runs(hot[:,ci,cj], 1)
        for s,e in runs:
            L = e-s+1
            lens[L] = lens.get(L,0)+1
        # MHW events with minlen 5 + join 2
        evs=[]
        r5 = find_runs(hot[:,ci,cj], 5)
        if r5:
            m=[r5[0][:]]
            for s,e in r5[1:]:
                gap = s-m[-1][1]-1
                if 1<=gap<=2: m[-1][1]=e
                else: m.append([s,e])
            evs=m
        for s,e in evs:
            n_per_cell_events += 1
            event_times.append((s,e,ci,cj))
            cells_with_events.setdefault((ci,cj), []).append((ds_[s], ds_[e]))

print("all hot-run length distribution:", dict(sorted(lens.items())))
print("hot cell-days total:", int(hot[:, sea].sum()))
print("per-cell MHW events:", n_per_cell_events)
print("distinct cells with >=1 MHW:", len(cells_with_events))
# unique event time spans
spans = {}
for s,e,ci,cj in event_times:
    spans.setdefault((s,e), 0)
    spans[(s,e)] += 1
for (s,e), c in sorted(spans.items()):
    print(f"  span {ds_[s]} -> {ds_[e]} ({e-s+1} d): {c} cells")
# are all events within 15..19 Aug?
print("all events within 2012-08-15..19:", all(15<=s and e<=19 for s,e,_,_ in event_times))
