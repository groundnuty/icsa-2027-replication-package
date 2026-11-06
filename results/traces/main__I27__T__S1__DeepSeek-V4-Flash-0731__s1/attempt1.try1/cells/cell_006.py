
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at s1z more carefully - maybe fs.ls has a limit
# Check if there are files beyond 1000
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(files))

# Let me try to list with different approaches
# Maybe use glob
import re
all_files = fs.glob('icsa2027_data_20261101T090944Z/s1z/*.nc')
print("Total glob:", len(all_files))
if len(all_files) > 0:
    print(all_files[:3])
    print(all_files[-3:])
