
script = '''
import sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import fsspec
sys.path.insert(0, "/work/mhw")
import common

def main(batch):
    fs = fsspec.filesystem("onedata")
    ext, tgt, done = common.load_state()
    ext_dates, tgt_dates = common.all_dates()
    allmap = {common.datekey(d): ("ext", i) for i, d in enumerate(ext_dates)}
    allmap.update({common.datekey(d): ("tgt", i) for i, d in enumerate(tgt_dates)})
    pending = [d for d in ext_dates + tgt_dates if common.datekey(d) not in done][:batch]
    t0 = time.time()
    ok, errs = [], []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {}
        for d in pending:
            futs[ex.submit(common.fetch_one, fs, d)] = d
        for fu in as_completed(futs):
            d = futs[fu]
            key = common.datekey(d)
            try:
                a = fu.result()
                name, i = allmap[key]
                (ext if name == "ext" else tgt)[i] = a
                ok.append(key)
            except Exception as e:
                errs.append((key, str(e)[:200]))
    common.save_state(ext, tgt, done | set(ok))
    print("batch=%d ok=%d errs=%d %.1fs total_done=%d/%d" % (
        len(pending), len(ok), len(errs), time.time() - t0, len(done) + len(ok), 4120))
    for k, e in errs[:5]:
        print("ERR", k, e)

if __name__ == "__main__":
    main(int(sys.argv[1]))
'''
with open('/work/mhw/run_batch.py','w') as fh:
    fh.write(script)
print('written')
