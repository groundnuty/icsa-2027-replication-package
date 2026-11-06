import fsspec
import os

fs = fsspec.filesystem('onedata')
all_files = fs.find('icsa2027_data_20261101T090944Z/s1z')
# Print number of files and range of years
years = []
for f in all_files:
    fname = os.path.basename(f)
    if fname.startswith('sst_') and fname.endswith('.nc'):
        years.append(fname[4:8])

if years:
    print(f"Total SST files in s1z: {len(years)}")
    print(f"Min year: {min(years)}, Max year: {max(years)}")
    # Check for specific years
    print(f"Count 2008: {years.count('2008')}")
    print(f"Count 1992: {years.count('1992')}")
else:
    print("No SST files in s1z.")
