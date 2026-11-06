import numpy as np

def mhw_runs(hot):
    def runs_of(mask):
        out, n, i = [], len(mask), 0
        while i < n:
            if mask[i]:
                j = i
                while j + 1 < n and mask[j+1]: j += 1
                out.append((i, j)); i = j + 1
            else:
                i += 1
        return out
    r = [r for r in runs_of(hot) if r[1]-r[0]+1 >= 5]
    merged = []
    for s, e in r:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged

# t: day index 0..19
t = "HHHHH..HHHHH...HHHHH....H"  # runs 0-4 (5), gap2 (5,6), 7-11 (5), gap3 (12,13,14), 15-19 (5)
r = mhw_runs([c=='H' for c in t])
print("gap2+gap3 case:", r, "expect [(0,11),(15,19)]")
t = "HHHHH.HHHHH"  # gap 1
print("gap1 case:", mhw_runs([c=='H' for c in t]), "expect [(0,9)]")
t = "HHHHH...HHHHH"  # gap 3 -> no merge
print("gap3 case:", mhw_runs([c=='H' for c in t]), "expect [(0,4),(8,12)]")
t = "HHH.HHHHH"  # short run before MHW, gap1 -> short run ignored
print("short-run case:", mhw_runs([c=='H' for c in t]), "expect [(5,9)]")
t = "HHHHH.HHHH.HHHHH"  # 5, gap1, 4 (short), gap1, 5 -> MHWs 0-4 and 11-15, between them: 1 non-hot+4 hot+1 non-hot = dist 6 -> no merge
print("sandwich case:", mhw_runs([c=='H' for c in t]), "expect [(0,4),(11,15)]")
t = "HHHHHH.HHHHH"  # 6, gap1, 5 -> merge
print("6+gap1+5:", mhw_runs([c=='H' for c in t]), "expect [(0,10)]")
