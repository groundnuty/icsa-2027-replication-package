script = open("/tmp/mhw_work/compute_stats.py").read()
old = """    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clim_raw[d-1] = np.nanmean(v2, axis=0)
        thresh_raw[d-1] = np.nanquantile(v2, 0.9, axis=0, method="hazen")"""
new = """    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clim_raw[d-1] = np.nanmean(v2, axis=0).reshape(nlat, nlon)
        thresh_raw[d-1] = np.nanquantile(v2, 0.9, axis=0, method="hazen").reshape(nlat, nlon)"""
assert old in script
open("/tmp/mhw_work/compute_stats.py", "w").write(script.replace(old, new))
print("patched")
exec(open("/tmp/mhw_work/compute_stats.py").read())
