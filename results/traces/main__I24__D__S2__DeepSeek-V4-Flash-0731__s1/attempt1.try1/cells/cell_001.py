
import fsspec
fs = fsspec.filesystem('onedata')
# Explore the dataset
print(fs.ls('/'))
