
import numpy as np, pickle
hot = np.load('/work/work/hot.npy')
M_old = np.load('/work/work/M.npy')
n = hot.shape[1]

def runs_of(b):
    out = []; i = 0
    while i < len(b):
        if b[i]:
            j = i
            while j+1 < len(b) and b[j+1]: j += 1
            out.append((i,j)); i = j+1
        else: i += 1
    return out

# Interpretation (a): merge consecutive MHW runs iff all days between are non-hot and count in {1,2}
M_a = np.zeros_like(hot)
for j in range(n):
    hcol = hot[:, j]
    r0 = [(a,b) for (a,b) in runs_of(hcol) if b-a+1 >= 5]
    merged = []
    for r in r0:
        if merged:
            gap = list(range(merged[-1][1]+1, r[0]))
            if len(gap) in (1,2) and not any(hcol[k] for k in gap):
                merged[-1] = (merged[-1][0], r[1])
            else:
                merged.append(r)
        else:
            merged.append(r)
    for (a,b) in merged:
        M_a[a:b+1, j] = True

print("M_old cell-days:", int(M_old.sum()), " M_a cell-days:", int(M_a.sum()))
print("cells changed:", int((M_a != M_old).any(axis=0).sum()))

active_a = M_a.any(axis=1)
active_old = M_old.any(axis=1)
print("active days old:", int(active_old.sum()), " a:", int(active_a.sum()))
print("active identical:", np.array_equal(active_old, active_a))
# show differences
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates = D['target']
for k in range(92):
    if active_old[k] != active_a[k]:
        print("  diff day:", target_dates[k].isoformat(), "old:", active_old[k], "a:", active_a[k])
# events for (a)
events_a = []
i = 0
while i < 92:
    if active_a[i]:
        j2 = i
        while j2+1 < 92 and active_a[j2+1]: j2 += 1
        events_a.append((target_dates[i].isoformat(), target_dates[j2].isoformat(), j2-i+1))
        i = j2+1
    else:
        i += 1
print("events (a):", events_a)

# example cell 1859 under (a)
j = 1859
print("cell 1859 (a) M:", ''.join('#' if M_a[k,j] else ('.' if hot[k,j] else '-') for k in range(92)))

np.save('/work/work/M_a.npy', M_a)
