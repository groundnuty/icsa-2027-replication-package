
import fsspec
fs = fsspec.filesystem('onedata')
files2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print(len(files2))
print(files2[:5])
print(files2[-5:])
