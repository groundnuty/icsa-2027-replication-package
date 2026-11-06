import fsspec, re, datetime as dt
fs = fsspec.filesystem('onedata')
base = "icsa2027_data_20261101T090944Z"
e2 = fs.ls(base + "/s2z")
n2 = [e.split('/')[-1] for e in e2 if e.endswith('.nc')]
print("s2z count:", len(n2))
dates2 = sorted(set(re.fullmatch(r'sst_(\d{8})\.nc', n).group(1) for n in n2 if re.fullmatch(r'sst_(\d{8})\.nc', n)))
print("s2z first/last:", dates2[:3], dates2[-3:])
# union with s1z dates
import pickle
d1 = pickle.load(open("/tmp/dataset_files.pkl","rb"))
all_dates = d1["dates"] | set(dates2)
print("union:", len(all_dates), "overlap:", len(d1["dates"] & set(dates2)))
s = sorted(all_dates)
print("union first/last:", s[:3], s[-3:])
# check contiguity
ds = [dt.datetime.strptime(x, "%Y%m%d").date() for x in s]
gaps = []
for i in range(1, len(ds)):
    if (ds[i]-ds[i-1]).days != 1:
        gaps.append((str(ds[i-1]), str(ds[i])))
print("gaps:", gaps[:20], "n gaps:", len(gaps))
pickle.dump(sorted(all_dates), open("/tmp/all_dates.pkl","wb"))