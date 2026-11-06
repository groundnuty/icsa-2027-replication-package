import fsspec

# Get all files and manually check the year extraction
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

print("Checking year extraction for first 10 files:")
baseline_years = list(range(1992, 2003))  # 1992-2002 inclusive
target_year = 2014

for i, f in enumerate(files[:10]):
    filename = f.split('/')[-1]  # Get just the filename
    date_part = filename.split('_')[1].split('.')[0]  # Gets '19820101'
    year = int(date_part[:4])
    print(f"{i}: {filename} -> date_part: {date_part}, year: {year}")
    
    if year in baseline_years:
        print(f"  -> Baseline year!")
    elif year == target_year:
        print(f"  -> Target year!")
    else:
        print(f"  -> Not in our period")