script = open("/tmp/mhw_work/compute_stats.py").read()
old = "    pool_counts_sea.append(cnt[finite_all])"
new = "    pool_counts_sea.append(cnt[finite_all_flat])"
assert old in script
script = script.replace(old, new)
old2 = "finite_all = np.isfinite(sst[targ_pos]).all(axis=0)"
new2 = "finite_all = np.isfinite(sst[targ_pos]).all(axis=0)\nfinite_all_flat = finite_all.reshape(-1)"
assert old2 in script
script = script.replace(old2, new2)
open("/tmp/mhw_work/compute_stats.py", "w").write(script)
print("patched")
exec(open("/tmp/mhw_work/compute_stats.py").read())
