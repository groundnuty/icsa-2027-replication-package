d=sorted(ds);print(d[0],d[-1],len(d))
fl2=fs.ls('icsa2027_data_20261101T090944Z/s1z',detail=True);print(len(fl2))
print(fs.exists('icsa2027_data_20261101T090944Z/s1z/sst_19920101.nc'),fs.exists('icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc'))
try:
  print(len(fs.find('icsa2027_data_20261101T090944Z/s1z')))
except Exception as e:print(e)