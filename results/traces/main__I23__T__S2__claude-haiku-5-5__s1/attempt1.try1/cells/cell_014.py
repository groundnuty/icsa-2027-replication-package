
import json
r=json.load(open('output/report.json'))
r['caveats']=("Region has 3309 sea cells of 3600 (land cells are NaN and set to 0). Only 5 cell-days across the region are in a per-cell MHW "
 "(one 5-day run in one cell), so the single regional event is a thin result. Only about 1.8% of sea cell-days in the target period exceed "
 "the threshold even though summer 2013 ran about 1 K warmer than the baseline mean; I did not verify this further. "
 "Grid coordinates are float32 from the dataset.")
json.dump(r,open('output/report.json','w'),indent=2); print(r['caveats'])
