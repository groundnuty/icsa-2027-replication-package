
import fsspec, re, datetime as dt
fs = fsspec.filesystem('onedata')
allf = fs.find('icsa2027_data_20261101T090944Z/s1z')
print(len(allf))
dates=sorted(re.search(r'sst_(\d{8})\.nc',f).group(1) for f in allf if re.search(r'sst_\d{8}\.nc$',f))
print(dates[0],dates[-1],len(dates),len(set(dates)))
print(sorted(set(f.split('/')[-1] for f in allf if not re.search(r'sst_\d{8}\.nc$',f)))[:10])
