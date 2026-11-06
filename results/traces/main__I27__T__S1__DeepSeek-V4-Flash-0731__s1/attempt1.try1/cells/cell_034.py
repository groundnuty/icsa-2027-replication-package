
import fsspec
fs = fsspec.filesystem('onedata')

# Check file sizes for some dates we need
for date in ['19911227', '19920101', '20030105', '20080601', '20080831']:
    path = f'icsa2027_data_20261101T090944Z/s1z/sst_{date}.nc'
    try:
        info = fs.info(path)
        print(f"{date}: size={info['size']}")
    except Exception as e:
        print(f"{date}: ERROR {e}")
