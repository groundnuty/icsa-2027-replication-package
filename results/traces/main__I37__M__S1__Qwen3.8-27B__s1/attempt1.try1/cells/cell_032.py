import time, datetime as dt, numpy as np, h5py
t0 = time.time()
ext = np.load('/work/chk/ext.npy').astype(np.float64)
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
print("ext_dates[1000]:", ext_dates[1000], " ext_dates[3000]:", ext_dates[3000])

base = "/data/icsa2027_data_20261101T090944Z/s1z"
def src_row(ymd):
    with h5py.File(f"{base}/sst_{ymd}.nc", 'r') as f:
        return f['analysed_sst'][0, 330:390, 551:611].astype(np.float32)

okc = 0
for idx in [0, 5, 1000, 2000, 3000, 4022, 4027]:
    d = ext_dates[idx]
    ymd = d.strftime('%Y%m%d')
    s = src_row(ymd)
    assert np.array_equal(ext[idx], s, equal_nan=True), f"ext row {idx} ({ymd})"
    okc += 1
for idx in [0, 45, 91]:
    d = tgt_dates[idx]
    ymd = d.strftime('%Y%m%d')
    s = src_row(ymd)
    assert np.array_equal(tgt[idx], s, equal_nan=True), f"tgt row {idx} ({ymd})"
    okc += 1
print("source spot-checks OK:", okc, "in", time.time()-t0)
