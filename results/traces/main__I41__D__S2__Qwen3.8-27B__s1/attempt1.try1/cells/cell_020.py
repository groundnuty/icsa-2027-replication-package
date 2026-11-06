path = '/work/verify1.py'
src = open(path).read()
old = """np.save('/work/tdoy.npy', np.array([doy_py(np.datetime_as_string(times[t0t+i], unit='D') and dt.date.fromisoformat(np.datetime_as_string(times[t0t+i], unit='D'))) for i in range(92)]))"""
new = """np.save('/work/tdoy.npy', np.array([doy_py(dt.date.fromisoformat(np.datetime_as_string(times[t0t+i], unit='D'))) for i in range(92)]))"""
assert old in src
src = src.replace(old, new)
open(path, 'w').write(src)

# add saves to pipeline
path = '/work/pipeline.py'
src = open(path).read()
old = """print("active days:", int(active.sum()), "events:", events)"""
new = """print("active days:", int(active.sum()), "events:", events)
np.save('/work/p_thr_s.npy', thr_s); np.save('/work/p_clim_s.npy', clim_s)
np.save('/work/p_mask.npy', mask); np.save('/work/p_sea.npy', sea)
import json as _json
_json.dump({"events": events}, open('/work/p_events.json', 'w'))"""
assert old in src
src = src.replace(old, new)
open(path, 'w').write(src)
print("patched both")
