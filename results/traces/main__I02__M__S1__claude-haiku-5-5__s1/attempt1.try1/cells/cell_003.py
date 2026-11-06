import os,re
files=sorted(os.listdir(d)); print(files[0],files[-1],len(files))
print(sorted(set(f[:4] for f in files)))
print(ds.analysed_sst.attrs, ds.attrs['comment'])
print(ds.analysed_sst.dtype, ds.latitude.values[[0,-1]], ds.longitude.values[[0,-1]])
print(sorted(set(f for f in files if not re.match(r'sst_\d{8}\.nc$',f))))