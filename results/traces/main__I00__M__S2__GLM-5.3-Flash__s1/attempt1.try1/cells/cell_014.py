import numpy as np, pickle, datetime as dtm, calendar

meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
ordered = meta["ordered"]
pos = {s: i for i, s in enumerate(ordered)}
n_ext = len(ordered)
in_win = np.load("/tmp/mhw_work/in_win.npy")

MDAYS = [31,29,31,30,31,30,31,31,30,31,30,31]
CUM = [0]
for nd in MDAYS: CUM.append(CUM[-1]+nd)
def doy_of_date(dt):
    return CUM[dt.month-1] + dt.day

# independent derivation: in_win2[d, s] = exists baseline date b with doy(b)==d and |s-b|<=5 days
in_win2 = np.zeros((367, n_ext), dtype=bool)
d0 = dtm.date(1992,1,1)
all_base = []
while d0 <= dtm.date(2002,12,31):
    all_base.append(d0); d0 += dtm.timedelta(days=1)
for b in all_base:
    d = doy_of_date(b)
    if d == 60:  # impossible (2000 is leap; 2000-02-29 is doy 60; skip? NO--)
        pass
    for k in range(-5, 6):
        s = b + dtm.timedelta(days=k)
        key = s.strftime("%Y-%m-%d")
        if key in pos:
            in_win2[d, pos[key]] = True
# note: baseline date 2000-02-29 has doy 60 -> its +-5 days feed... doy 60 has no pool of its own,
# but under the literal definition those days also are within +-5 of OTHER baseline dates' doys, fine.
# Remove any marking of window 60 (no pool of its own):
in_win2[60, :] = False

same = (in_win == in_win2).all()
print("in_win matches independent derivation:", same)
if not same:
    diff = np.argwhere(in_win != in_win2)
    print("n diffs:", len(diff))
    for d, s in diff[:20]:
        print("  doy", d, ordered[s], "build:", in_win[d,s], "indep:", in_win2[d,s])

# extra invariant checks
cnt = np.array([in_win[d].sum() for d in range(1,367) if d != 60])
print("window sizes all == 121:", bool((cnt == 121).all()))
# doy 60 must be empty
print("doy 60 window empty:", bool((~in_win[60]).all()))
# the only non-baseline days used:
base_set = set(dtm.date(1992,1,1)+dtm.timedelta(days=i) for i in range((dtm.date(2002,12,31)-dtm.date(1992,1,1)).days+1))
used = [ordered[i] for i in np.where(in_win.any(axis=0))[0]]
nonbase_used = [s for s in used if dtm.date(*map(int, s.split("-"))) not in base_set]
print("non-baseline days used:", nonbase_used)
# every baseline date is used by at least one window?
missing = [b.strftime("%Y-%m-%d") for b in all_base if not in_win[:, pos[b.strftime('%Y-%m-%d')]].any()]
print("baseline dates in no window:", len(missing), missing[:10])
