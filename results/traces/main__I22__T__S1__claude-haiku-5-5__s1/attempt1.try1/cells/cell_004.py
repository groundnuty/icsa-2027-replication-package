
import collections
print(collections.Counter(n[4:8] for n in names))
for p in ['icsa2027_data_20261101T090944Z/s1z/sst_19920101.nc','icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc']:
    try:
        print(p, fs.exists(p), fs.info(p).get('size'))
    except Exception as e: print(p,'ERR',e)
print(ds.analysed_sst.encoding, ds.analysed_sst.attrs)
