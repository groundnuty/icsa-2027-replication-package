import os, json
for f in ["output/mhw_mask.nc", "output/report.json"]:
    print(f, os.path.getsize(f), "bytes")
print(json.load(open("output/report.json")))
