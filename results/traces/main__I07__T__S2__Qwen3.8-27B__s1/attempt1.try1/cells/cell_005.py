
import fsspec, h5netcdf, time, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
h = h5netcdf.File(f, mode='r')
hf = h._h5file
raw = hf['/analysed_sst']
print("h5py dataset chunks:", raw.chunks, "shape:", raw.shape, "fillvalue:", raw.fillvalue, "compression:", raw.compression)
rawt = hf['/time']
print("time fillvalue:", rawt.fillvalue)
lat1 = hf['/latitude']; print("lat chunks:", lat1.chunks)
# probe: 40-day block
t0 = time.time()
y = h['analysed_sst'][1000:1040, 48:108, 353:413]
dt = time.time()-t0
print("40-day 60x60: %.2fs  %.3f s/day" % (dt, dt/40))
# probe: 200-day block
t0 = time.time()
z = h['analysed_sst'][1000:1200, 48:108, 353:413]
dt = time.time()-t0
print("200-day 60x60: %.2fs  %.3f s/day" % (dt, dt/200))
h.close(); f.close()
