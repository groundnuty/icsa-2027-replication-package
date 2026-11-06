import xarray as xr, numpy as np, json
d = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(d)
mv = d['mhw']
print('dtype:', mv.dtype, '| dims:', mv.dims, '| unique:', np.unique(mv.values))
print('time:', str(d.time.values[0])[:10], '..', str(d.time.values[-1])[:10], '| ntime:', d.sizes['time'])
print('lat:', float(d.lat[0]), '..', float(d.lat[-1]), '| lon:', float(d.lon[0]), '..', float(d.lon[-1]))
print('sum:', int(mv.values.sum()), '(expect 28140)')
rep = json.load(open('/work/output/report.json'))
print('report keys:', sorted(rep.keys()))
print('events:', rep['events'])
# consistency: active days of mask == event days
active = mv.values.sum(axis=(1,2)) > 0
import datetime as dtm
ad = [str(x)[:10] for x in d.time.values[active]]
print('first/last active day in mask:', ad[0], ad[-1], '| n active:', len(ad), '(expect 17)')
assert ad[0]=='2009-06-24' and ad[-1]=='2009-07-10' and len(ad)==17
# verify contiguity of active days
tt = d.time.values[active].astype('datetime64[D]')
assert np.all(np.diff(tt).astype(int)==1)
print('all checks passed')