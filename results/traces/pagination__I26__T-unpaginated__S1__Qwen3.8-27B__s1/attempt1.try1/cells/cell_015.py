s = open('/work/mhw_analyse.py').read()
old = "Rmin = np.minimum.accumulate(np.where(g, ar[:, None], big), axis=0)"
new = "Rmin = np.minimum.accumulate(np.where(g, ar[:, None], big)[::-1], axis=0)[::-1]"
assert old in s
s = s.replace(old, new)
open('/work/mhw_analyse.py', 'w').write(s)
print("patched")
