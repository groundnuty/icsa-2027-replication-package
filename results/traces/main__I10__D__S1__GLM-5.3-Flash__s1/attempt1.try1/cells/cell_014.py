import numpy as np, datetime as dt, json, warnings
warnings.filterwarnings('ignore')

hot = np.load('/work/hot.npy')      # (92,60,60) bool
sea = np.load('/work/sea.npy')      # (60,60) bool
T = np.load('/work/target_sst.npy')
tstr = np.load('/work/target_datestr.npy')
nt = hot.shape[0]

def runs_of_true(h):
    """list of (start,end) inclusive for consecutive True runs, 1-D bool"""
    idx = np.flatnonzero(h)
    if idx.size==0: return []
    br = np.flatnonzero(np.diff(idx)>1)
    starts = np.concatenate([[idx[0]], idx[br+1]])
    ends   = np.concatenate([idx[br], [idx[-1]]])
    return list(zip(starts.tolist(), ends.tolist()))

def cell_mhw_intervals(h):
    """hot runs >=5 days, then join runs separated by 1-2 non-hot days; return final intervals."""
    runs = [(s,e) for s,e in runs_of_true(h) if e-s+1>=5]
    if not runs: return []
    merged = [list(runs[0])]
    for s,e in runs[1:]:
        gap = s - merged[-1][1] - 1
        if gap <= 2:      # 1 or 2 non-hot days between MHWs -> join (gap==0 impossible for distinct runs)
            merged[-1][1] = e
        else:
            merged.append([s,e])
    return [(s,e) for s,e in merged]

mhw = np.zeros(hot.shape, np.uint8)
n_cell_events = 0; cell_event_days = 0; lens = []
for r in range(60):
    for c in range(60):
        if not sea[r,c]: continue
        iv = cell_mhw_intervals(hot[:,r,c])
        for s,e in iv:
            mhw[s:e+1, r, c] = 1
            n_cell_events += 1; cell_event_days += e-s+1; lens.append(e-s+1)
print('per-cell MHWs:', n_cell_events, '| total cell-days:', cell_event_days,
      '| mean length:', round(float(np.mean(lens)),1), '| max:', max(lens), '| min:', min(lens))
print('mhw fraction on sea cells:', round(mhw[:,sea].sum()/(sea.sum()*nt)*100,2), '%')

# sanity: mask implies >=5 days in every per-cell event (post-join, events only grow)
# regional events
active = mhw.any(axis=(1,2)) & np.isfinite(T).all(axis=(1,2)).any()  # mhw already only on sea cells
active = mhw.any(axis=(1,2))
ev = runs_of_true(active)
dates = [dt.date(int(s[:4]),int(s[4:6]),int(s[6:])) for s in tstr]
events_json = [{'onset': dates[s].isoformat(), 'end': dates[e].isoformat()} for s,e in ev]
print('regional events:', len(ev))
for (s,e),je in zip(ev,events_json):
    print(f'  {je["onset"]} -> {je["end"]}  ({e-s+1} days)  peak active cells: {int(mhw[s:e+1].sum(axis=(1,2)).max())}')
print('active days total:', int(active.sum()), 'of', nt)
print('hot-vs-mhw day overlap check: any mhw day not hot?',
      bool((mhw.astype(bool) & ~hot)[:, sea].any()))   # gap-joined days may be non-hot (expected)

np.save('/work/mhw.npy', mhw)
with open('/work/events.json','w') as f: json.dump(events_json, f, indent=1)
