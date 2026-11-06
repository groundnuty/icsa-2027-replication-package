
import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
files = sorted(e.split('/')[-1] for e in entries if e.endswith('.nc'))
print("num files:", len(files))
print("first:", files[0], "last:", files[-1])
# check for any non sst files
others = [e for e in entries if not e.endswith('.nc')]
print("others:", others)
# years present
years = sorted(set(f[4:8] for f in files))
print("years:", years[:5], "...", years[-5:])
print("num years:", len(years))
