import os,collections
D='/data/icsa2027_data_20261101T090944Z/s1z'
fs=sorted(os.listdir(D)); print(fs[0],fs[-1],len(fs))
print([f for f in fs if not f.startswith('sst_')][:10])
ys=collections.Counter(f[4:8] for f in fs); print(sorted(ys.items())[:3], sorted(ys.items())[-3:])
print(sorted(f for f in fs if f[4:8] in('1991','2003','2005') and not(f[4:8]=='2005' and f[8:10] in ('06','07','08')))[:3])