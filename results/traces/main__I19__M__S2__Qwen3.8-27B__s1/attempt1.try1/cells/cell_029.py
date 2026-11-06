src = open('/work/verify.py').read()
src = src.replace("""    i = int(np.searchsorted(ds.time.values, np.datetime64(datestr)))
    assert str(ds.time[i].astype('datetime64[D]')) == datestr[:10]
    return float(ds.analysed_sst[i, li, lo].values)""",
"""    i = int(np.searchsorted(ds.time.values, np.datetime64(datestr)))
    assert str(ds.time.values[i].astype('datetime64[D]')) == datestr[:10], (datestr, ds.time.values[i])
    return float(ds.analysed_sst[i, li, lo].values)""")
open('/work/verify.py','w').write(src)
import runpy
runpy.run_path('/work/verify.py', run_name='__main__')
