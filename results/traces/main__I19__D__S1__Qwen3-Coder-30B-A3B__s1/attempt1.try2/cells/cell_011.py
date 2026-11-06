import fsspec

# Get all files and see what years we actually have
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

# Find all unique years in the dataset
years = set()
for f in files:
    filename = f.split('/')[-1]  # Get just the filename
    date_part = filename.split('_')[1].split('.')[0]  # Gets '19820101'
    year = int(date_part[:4])
    years.add(year)

print("Available years in dataset:", sorted(list(years)))
print("Number of files:", len(files))

# Check specifically for years 1992-2002 and 2014
baseline_years = list(range(1992, 2003))  # 1992-2002 inclusive
target_year = 2014

baseline_files = [f for f in files if int(f.split('/')[-1].split('_')[1].split('.')[0][:4]) in baseline_years]
target_files = [f for f in files if int(f.split('/')[-1].split('_')[1].split('.')[0][:4]) == target_year]

print(f"\nFiles from 1992-2002: {len(baseline_files)}")
print(f"Files from 2014: {len(target_files)}")

if len(baseline_files) == 0:
    print("Warning: No baseline files found in expected range.")
    # Let's see if we can use a broader range
    print("Files from 1982-1991 (earlier years):", len([f for f in files if 1982 <= int(f.split('/')[-1].split('_')[1].split('.')[0][:4]) <= 1991]))
    print("Files from 2003-2013 (later years):", len([f for f in files if 2003 <= int(f.split('/')[-1].split('_')[1].split('.')[0][:4]) <= 2013]))