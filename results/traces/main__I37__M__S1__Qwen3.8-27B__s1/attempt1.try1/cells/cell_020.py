import numpy as np, h5py, datetime as dt

def read_raw(path, n):
    raw = np.fromfile(path, dtype=np.float32)
    assert raw.size >= n
    return raw[:n].reshape(-1, 60, 60), raw[n:]

ext, ext_tail = read_raw('/tmp/mhw/sst_ext.npy', 4028*3600)
tgt, tgt_tail = read_raw('/tmp/mhw/sst_tgt.npy', 92*3600)
print("ext tail (extra 32):", ext_tail[:8])
print("ext row4027 last 32:", ext[-1].ravel()[-32:-24], "...")
print("tail==row4027 last32:", np.array_equal(ext_tail, ext[-1].ravel()[-32:], equal_nan=True))
print("tgt tail==row91 last32:", np.array_equal(tgt_tail, tgt[-1].ravel()[-32:], equal_nan=True))
print("ext row0 first 8:", ext[0].ravel()[:8])
print("tgt row0 first 8:", tgt[0].ravel()[:8])

# verify against source files
base = "/data/icsa2027_data_20261101T090944Z/s1z"
def src_row(ymd):
    with h5py.File(f"{base}/sst_{ymd}.nc", 'r') as f:
        return f['analysed_sst'][0, 330:390, 551:611].astype(np.float32)

checks_ext = {0:"19911227", 4:"19920104", 5:"19920101", 2000:"19970714", 4022:"20021231", 4023:"20030101", 4027:"20030105"}
for idx, ymd in checks_ext.items():
    s = src_row(ymd)
    ok = np.array_equal(ext[idx], s, equal_nan=True)
    print("ext", idx, ymd, "match:", ok, "" if ok else (ext[idx][:2].ravel()[:4], s.ravel()[:4]))

checks_tgt = {0:"20120601", 45:"20120716", 91:"20120831"}
for idx, ymd in checks_tgt.items():
    s = src_row(ymd)
    ok = np.array_equal(tgt[idx], s, equal_nan=True)
    print("tgt", idx, ymd, "match:", ok, "" if ok else (tgt[idx][:2].ravel()[:4], s.ravel()[:4]))
