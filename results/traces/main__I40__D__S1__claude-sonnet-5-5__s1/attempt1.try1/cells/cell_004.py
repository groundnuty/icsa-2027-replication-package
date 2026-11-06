print(fs.exists(R+'/sst_19920101.nc'),fs.exists(R+'/sst_20021231.nc'),fs.exists(R+'/sst_20030105.nc'),fs.exists(R+'/sst_19911227.nc'))
fl2=fs.find(R);print(len(fl2))
print(x.analysed_sst.attrs, float(x.analysed_sst.max()))