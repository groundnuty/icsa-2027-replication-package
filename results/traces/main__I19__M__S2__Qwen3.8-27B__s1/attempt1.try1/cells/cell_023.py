src = open('/work/pipeline2.py').read()
old = """pool = np.array(pool)
n = int(np.isfinite(pool).sum())"""
new = """pool = np.array(pool)
n = int(np.isfinite(pool).sum())
if n == 0:
    print("cell0 all-NaN pool; finding a data cell...")
    for c2 in range(ncells):
        li2 = c2 // 60; lo2 = c2 % 60
        vals = [float(ds.analysed_sst[int(np.searchsorted(ds.time.values, np.datetime64('2000-06-01'))), li2, lo2].values) for _ in [0]]
        if np.isfinite(vals[0]):
            li, lo = li2, lo2
            c0 = c2
            pool = []
            for Y in range(1992, 2003):
                b = date(Y, 6, 1)
                for k in range(-5, 6):
                    d = b + timedelta(days=k)
                    i = int(np.searchsorted(ds.time.values, np.datetime64(f"{d.year:04d}-{d.month:02d}-{d.day:02d}")))
                    pool.append(float(ds.analysed_sst[i, li, lo].values))
            pool = np.array(pool)
            n = int(np.isfinite(pool).sum())
            break
print("verify cell (li,lo) =", li, lo, " flat idx", li*60+lo)"""
assert old in src
src = src.replace(old, new)
src = src.replace('print("cell0 doy153:', 'print("cell(li,lo) doy153:')
src = src.replace("print("mean check:", np.nanmean(pool), clim[152,0], np.isclose(np.nanmean(pool), clim[152,0]))",
                  "print("mean check:", np.nanmean(pool), clim[152, li*60+lo], np.isclose(np.nanmean(pool), clim[152, li*60+lo]))")
src = src.replace("q_manual, thr[152, 0],", "q_manual, thr[152, li*60+lo],")
open('/work/pipeline2.py','w').write(src)
import runpy
runpy.run_path('/work/pipeline2.py', run_name='__main__')
