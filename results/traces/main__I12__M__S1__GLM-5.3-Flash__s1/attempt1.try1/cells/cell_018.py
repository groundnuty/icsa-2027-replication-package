import numpy as np, pickle
hot_data = np.load('/tmp/mhw_mask.npy')
with open('/tmp/percell.pkl','rb') as f:
    per_cell_events, td_list, ev, sea = pickle.load(f)
durs = [ (e-s+1) for v in per_cell_events.values() for (s,e) in v ]
import collections
print('per-cell event durations histogram:', dict(sorted(collections.Counter(durs).items())))
print('num per-cell events total:', len(durs))
n_events_per_cell = collections.Counter(len(v) for v in per_cell_events.values())
print('events per cell:', dict(sorted(n_events_per_cell.items())))
# hotspot of first event onsets
onsets = collections.Counter(td_list[v[0][0]] for v in per_cell_events.values())
print('first-event onset counts:', dict(sorted(onsets.items())))
# check a specific cell
cell = (30,30)
print('cell (30,30) events:', [(td_list[s], td_list[e], e-s+1) for s,e in per_cell_events[cell]])
