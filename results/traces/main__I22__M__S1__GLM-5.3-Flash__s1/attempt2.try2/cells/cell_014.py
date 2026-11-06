import h5py, datetime as dt
d = '/data/icsa2027_data_20261101T090944Z/s1z'
for date in ['19911227','20040601','20030821']:
    with h5py.File(f'{d}/sst_{date}.nc','r') as f:
        tv = f['time']
        print(date, 'attrs:', dict(tv.attrs))
        print('   raw:', tv[:], tv.dtype)
