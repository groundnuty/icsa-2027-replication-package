import numpy as np, h5py, fsspec, datetime
# 1) hazen percentile check
x = np.array([1.,2,3,4,5,6,7,8,9,10])
print('hazen p90 of 1..10:', np.percentile(x, 90, method='hazen'))  # expect 9.1? hazen: p*(n+... ) check
# MATLAB quantile default: type 5. For x=1..10, q(0.9) = ?
# type5: h = p*n + 0.5 = 9.5 -> q = x[9] (0-based floor 9) + ... h=9.5 -> between x[8]=9 and x[9]=10? floor(9.5)=9 -> x[8]+0.5*(x[9]-x[8]) hmm
# Actually h = 0.9*10 + 0.5 = 9.5; q = x(9) + (0.5)*(x(10)-x(9)) = 9.5
print('manual hazen:', 9 + 0.5*(10-9))
# 2) spot check files
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
for name in ['sst_19911227.nc','sst_19920229.nc','sst_19961231.nc','sst_20030105.nc','sst_20150601.nc','sst_20150831.nc']:
    f = fs.open(base+name,'rb')
    with h5py.File(f,'r') as h:
        t = h['time'][:]  # seconds since 1981-01-01
        import numpy as _np
        dt = datetime.date(1981,1,1)+datetime.timedelta(seconds=int(t[0]))
        lat = h['latitude'][218:220]; lon = h['longitude'][601:603]
        sh = h['analysed_sst'].shape
    f.close()
    print(name, '-> file time', dt, 'shape', sh, 'lat', lat, 'lon', lon)
