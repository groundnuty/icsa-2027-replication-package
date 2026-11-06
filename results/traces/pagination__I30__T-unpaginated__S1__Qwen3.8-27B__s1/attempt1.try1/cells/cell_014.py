
import sys, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0,'/work/mhw')
import common
import fsspec

fs = fsspec.filesystem('onedata')
ext, tgt, done = common.load_state()
ext_dates, tgt_dates = common.all_dates()
allmap = {common.datekey(d): ('ext', i) for i, d in enumerate(ext_dates)}
allmap.update({common.datekey(d): ('tgt', i) for i, d in enumerate(tgt_dates)})

pending = [d for d in ext_dates + tgt_dates if common.datekey(d) not in done][:100]
print('pending batch:', len(pending), pending[0], '->', pending[-1])

t0 = time.time()
def work(d):
    a = common.fetch_one(fs, d)
    key = common.datekey(d)
    arr, i = allmap[key]
    (ext if arr=='ext' else tgt)[i] = a
    return key

ok, errs = 0, []
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = [ex.submit(work, d) for d in pending]
    for fu in as_completed(futs):
        try:
            fu.result(); ok += 1
        except Exception as e:
            errs.append(str(e))
            if len(errs) < 3: print('ERR', errs[-1])
print('done in', round(time.time()-t0,1), 's; ok', ok, 'errs', len(errs))
done.update(common.datekey(d) for d in pending if common.datekey(d) in {common.datekey(d) for d in pending})  # placeholder
# save only actually-fetched keys: recompute from array finiteness
fetched = [common.datekey(d) for d in pending if not np.isnan((ext[allmap[common.datekey(d)][1]] if allmap[common.datekey(d)][0]=='ext' else tgt[allmap[common.datekey(d)][1]]).all())]
print('fetched ok:', len(fetched))
common.save_state(ext, tgt, done | set(fetched))
print('state saved, total done:', len(done | set(fetched)))
