import fsspec, os, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
LDIR='/work/nc'
os.makedirs(LDIR, exist_ok=True)

def daterange(a,b):
    d=a
    while d<=b:
        yield d
        d+=dt.timedelta(days=1)

all_dates=[d for d in daterange(dt.date(1991,12,27), dt.date(2004,8,31))]
print('total files needed:', len(all_dates))

def have(d):
    p=os.path.join(LDIR, d.strftime('sst_%Y%m%d.nc'))
    return os.path.exists(p) and os.path.getsize(p)>100000

todo=[d for d in all_dates if not have(d)]
print('remaining to download:', len(todo))

def work(args):
    i,d=args
    lp=os.path.join(LDIR, d.strftime('sst_%Y%m%d.nc'))
    rp=base+d.strftime('sst_%Y%m%d.nc')
    for attempt in range(3):
        try:
            if os.path.exists(lp):
                os.remove(lp)
            fs.get(rp, lp)
            if os.path.exists(lp) and os.path.getsize(lp)>100000:
                return 1
        except Exception as e:
            time.sleep(2)
    return 0

t0=time.time()
ok=0; fail=[]
B=900
for bi in range(0, len(todo), B):
    batch=todo[bi:bi+B]
    with ThreadPoolExecutor(max_workers=12) as exx:
        res=list(exx.map(work, enumerate(batch)))
    ok+=sum(res)
    fb=[d for d,r in zip(batch,res) if r==0]
    fail+=fb
    el=time.time()-t0
    print(f'batch {bi}+{len(batch)}: ok_now={sum(res)} fail_now={len(fb)} total_ok={ok} elapsed={el:.0f}s rate={(ok/el):.1f} files/s', flush=True)

print('TOTAL downloaded ok:', ok)
print('failures:', len(fail), [str(d) for d in fail[:20]])
