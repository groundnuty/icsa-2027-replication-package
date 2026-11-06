start=dt.date(1991,12,27); end=dt.date(2003,1,5)
days=[start+dt.timedelta(i) for i in range((end-start).days+1)]
tstart=dt.date(2010,6,1); tend=dt.date(2010,8,31)
tdays=[tstart+dt.timedelta(i) for i in range((tend-tstart).days+1)]
alld=days+tdays
def get(date):
    s=date.strftime('%Y%m%d')
    with fs.open(P+f'sst_{s}.nc','rb') as f:
        x=xr.open_dataset(f,engine='h5netcdf')
        v=x.analysed_sst.values[0][np.ix_(ilat,ilon)].astype(np.float64)
        x.close()
    return v
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(get,alld))
arr=np.stack(res)
print(arr.shape, np.isnan(arr).mean())
np.savez('/tmp/sst_region.npz', arr=arr, days=np.array([x.isoformat() for x in alld]), lat=lat[ilat], lon=lon[ilon])
print(np.nanmin(arr), np.nanmax(arr))