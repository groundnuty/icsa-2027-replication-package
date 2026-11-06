import numpy as np
from scipy import ndimage

def mhw_mask_loop(h):
    h = np.asarray(h, bool); n = len(h)
    runs = []; i = 0
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]: j += 1
            if j-i+1 >= 5: runs.append([i, j])
            i = j+1
        else: i += 1
    merged = []
    for r in runs:
        if merged and r[0]-merged[-1][1]-1 <= 2: merged[-1][1] = r[1]
        else: merged.append(r)
    m = np.zeros(n, np.uint8)
    for s, e in merged: m[s:e+1] = 1
    return m

def mhw_mask_label(h):
    h = np.asarray(h, bool); n = len(h)
    lab, k = ndimage.label(h)
    runs = []
    for kk in range(1, k+1):
        idx = np.where(lab == kk)[0]
        if len(idx) >= 5: runs.append([idx[0], idx[-1]])
    merged = []
    for r in runs:
        if merged and r[0]-merged[-1][1]-1 <= 2: merged[-1][1] = r[1]
        else: merged.append(r)
    m = np.zeros(n, np.uint8)
    for s, e in merged: m[s:e+1] = 1
    return m

cases = {
  "single 5-run":              "0001111100000000",
  "single 4-run (no mhw)":     "00011110000000000000",
  "5 + 2gap + 5 (join)":       "001111100111110000000",
  "5 + 3gap + 5 (no join)":    "001111100011111000000",
  "5 + 1gap + 5 + 2gap + 6":   "00111110111110011111100",
  "4 + 1gap + 4 (no mhw)":     "0011110111100000000000",
  "5 + 2gap + 4 (no join)":    "0011111001111000000000",
  "full run":                  "1111111111111111",
  "5 at start":                "11111000000000000000",
  "5 at end":                  "000000000000000011111",
  "6 + 2gap + 6":              "011111100111111000000",
  "5+1+5+1+5":                 "0111110111110111110",
}
ok = True
for name, s in cases.items():
    h = np.array([c == '1' for c in s])
    a = mhw_mask_loop(h); b = mhw_mask_label(h)
    same = np.array_equal(a, b)
    print(f"{name:28s} mask={''.join(a.astype(str))} ok={same}")
    ok &= same
print("ALL SYNTHETIC OK:", ok)

import os, json
print("\nfinal outputs:")
for f in ['mhw_mask.nc', 'report.json']:
    p = f'/work/output/{f}'
    print(" ", f, os.path.getsize(p), "bytes")
print(json.dumps(json.load(open('/work/output/report.json')), indent=1))
