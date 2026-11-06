import numpy as np, pickle, datetime as dtm, calendar

meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
ordered = meta["ordered"]
pos = {s: i for i, s in enumerate(ordered)}
n_ext = len(ordered)

MDAYS = [31,29,31,30,31,30,31,31,30,31,30,31]
CUM = [0]
for nd in MDAYS: CUM.append(CUM[-1]+nd)
def md_of_doy(d):
    m = 1
    while m <= 12 and CUM[m] < d:
        m += 1
    return m, d - CUM[m-1]

in_win = np.zeros((367, n_ext), dtype=bool)
for d in range(1, 367):
    if d == 60:
        continue
    m0, day0 = md_of_doy(d)
    wset = set()
    for y in range(1992, 2003):
        try:
            center = dtm.date(y, m0, day0)
        except ValueError:
            continue  # Feb 29 in a non-leap baseline year: no such baseline date
        k = 1
        while k <= 5:
            wset.add((center - dtm.timedelta(days=k)).strftime("%Y-%m-%d"))
            wset.add((center + dtm.timedelta(days=k)).strftime("%Y-%m-%d"))
            k += 1
        wset.add(center.strftime("%Y-%m-%d"))
    for s in wset:
        in_win[d, pos[s]] = True

counts = np.array([in_win[d].sum() for d in range(1, 367) if d != 60])
print("window counts: min", counts.min(), "max", counts.max())
print("doy 1 count:", in_win[1].sum(), "| doy 2:", in_win[2].sum(), "| doy 59:", in_win[59].sum(),
      "| doy 61:", in_win[61].sum(), "| doy 150:", in_win[150].sum(), "| doy 366:", in_win[366].sum())

# membership spot checks
checks = [
    (1, "1991-12-27", True), (1, "1991-12-31", True), (1, "1991-12-26", False),
    (2, "1991-12-28", True), (2, "1991-01-01", False),
    (366, "2003-01-05", True), (366, "2003-01-06", False), (366, "1991-12-26", True),
    (59, "1992-02-29", True), (61, "1992-02-29", True), (60, "1992-02-29", False),
    (150, "1991-05-25", False), (150, "2002-06-04", True),
    (5, "1991-12-31", True), (5, "1991-12-26", False),
    (362, "2003-01-02", True),
]
ok = True
for d, s, expect in checks:
    got = bool(in_win[d, pos[s]])
    status = "OK" if got == expect else "MISMATCH"
    if got != expect: ok = False
    print(f"  doy {d} in-window {s}: {got} (expect {expect}) {status}")
print("all spot checks passed:", ok)

# every window member must lie in 1991-12-27..2003-01-05
idxs = np.where(in_win.any(axis=0))[0]
print("window member date range:", ordered[idxs.min()], "->", ordered[idxs.max()])
lo, hi = pos["1991-12-27"], pos["2003-01-05"]
print("all members within allowed range:", bool(idxs.min() >= lo and idxs.max() <= hi))
# each extension day belongs to how many windows?
per_day = in_win.sum(axis=0)
print("windows per day (nonzero part) unique:", np.unique(per_day[per_day > 0]))
print("days in no window:", int((per_day == 0).sum()), "(should be all of 1991-01-01..1991-12-26 and 2003-01-06..2003-12-31 + target days)")
np.save("/tmp/mhw_work/in_win.npy", in_win)
print("in_win saved")
