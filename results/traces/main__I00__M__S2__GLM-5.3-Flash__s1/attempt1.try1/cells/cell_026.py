import numpy as np

def find_runs(bool_arr):
    runs = []; n = len(bool_arr); i = 0
    while i < n:
        if bool_arr[i]:
            j = i
            while j+1 < n and bool_arr[j+1]: j += 1
            runs.append((i, j)); i = j+1
        else:
            i += 1
    return runs

def detect(h):
    runs = [r for r in find_runs(h) if r[1]-r[0]+1 >= 5]
    if not runs: return np.zeros(len(h), bool)
    merged = [list(runs[0])]
    for (s, e) in runs[1:]:
        gap = s - merged[-1][1] - 1
        if gap in (1, 2): merged[-1][1] = e
        else: merged.append([s, e])
    m = np.zeros(len(h), bool)
    for (s, e) in merged: m[s:e+1] = True
    return m

tests = {
    "len-4 run (too short)":            [1,1,1,1,0,0,0,0,0,0],
    "len-5 run":                        [0,0,1,1,1,1,1,0,0,0],
    "5 + gap1 + 5 joined":              [1,1,1,1,1,0,1,1,1,1,1,0,0],
    "5 + gap2 + 5 joined":              [1,1,1,1,1,0,0,1,1,1,1,1],
    "5 + gap3 + 5 separate":            [1,1,1,1,1,0,0,0,1,1,1,1,1],
    "run4 gap1 run4 gap1 run4 joined":  [1,1,1,1,0,1,1,1,1,0,1,1,1,1],
    "single days only":                 [1,0,1,0,1,0,1,0,1,0],
}
for name, arr in tests.items():
    h = np.array(arr, bool)
    m = detect(h)
    print(f"{name:35s} -> mask {m.astype(int)}")
