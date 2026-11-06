
main = r'''
exec(open('/work/common.py').read())
dd = doy(ttimes)
th = thrS[dd-1]  # (92,60,60)
hot = (T >= th) & finite_all[None]
# per-cell MHW: runs >=5 hot days, then join separated by 1-2 non-hot days
nT,nY,nX = hot.shape
mhw = np.zeros_like(hot)
def runs(x):
    # x 1D bool -> list of (start,end) inclusive
    r=[]; i=0; n=len(x)
    while i<n:
        if x[i]:
            j=i
            while j+1<n and x[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
nev=0
for y in range(nY):
    for x in range(nX):
        if not finite_all[y,x]: continue
        rr=[r for r in runs(hot[:,y,x]) if r[1]-r[0]+1>=5]
        if not rr: continue
        # join
        merged=[list(rr[0])]
        for s,e in rr[1:]:
            if s-merged[-1][1]-1 <= 2:  # gap days = s-prev_end-1
                merged[-1][1]=e
            else:
                merged.append([s,e])
        for s,e in merged:
            mhw[s:e+1,y,x]=True; nev+=1
active = mhw.any(axis=(1,2))
# regional events: maximal runs of active days
ev=[]; i=0
while i<nT:
    if active[i]:
        j=i
        while j+1<nT and active[j+1]: j+=1
        ev.append((str(ttimes[i].date()), str(ttimes[j].date()), int(j-i+1)))
        i=j+1
    else: i+=1
print('per-cell MHW count', nev, 'hot cell-days', int(hot.sum()), 'mhw cell-days', int(mhw.sum()))
print('active days', int(active.sum()))
print('events', ev)
# write outputs
latv = ds.latitude.values[la]; lonv = ds.longitude.values[lo]
out = xr.Dataset({'mhw': (('time','lat','lon'), mhw.astype(np.uint8))},
    coords={'time': ttimes.values, 'lat': latv, 'lon': lonv})
out.mhw.attrs={'long_name':'marine heatwave per-cell mask'}
out.to_netcdf('/work/output/mhw_mask.nc')
rep = {
 'region': {'lat_min': float(latv.min()), 'lat_max': float(latv.max()), 'lon_min': float(lonv.min()), 'lon_max': float(lonv.max())},
 'baseline_analysed': {'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed': {'start': str(ttimes[0].date()), 'end': str(ttimes[-1].date())},
 'events': [{'onset':a,'end':b} for a,b,_ in ev],
 'complete': True,
 'caveats': ("Per-cell MHWs: runs >=5 hot days first, then joined when separated by 1-2 non-hot days (gap days included). "
   "Cells with any NaN in target period excluded (land/partly missing); their mask is 0. Region grid cells 63.32-64.50 N, 21.32-22.50 E (60x60 native 0.02 deg grid). "
   "Thresholds/climatology use 1992-2002 baseline with pools from 1991-12-27 to 2003-01-05 windows.")
}
json.dump(rep, open('/work/output/report.json','w'), indent=2)
print(json.dumps(rep, indent=1))
'''
open('/work/main.py','w').write(main)
r=subprocess.run(['python','/work/main.py'],capture_output=True,text=True); print(r.stdout[-6000:], r.stderr[-3000:])
