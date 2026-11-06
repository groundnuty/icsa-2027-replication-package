s=open('/work/fetch.py').read()
s=s.replace("""    fs.get(f'{base}/sst_{d:%Y%m%d}.nc', raw)
    with xr.open_dataset(raw, engine='h5netcdf') as ds:
        lat=ds.latitude.values; lon=ds.longitude.values
        ri=np.where((lat>=63.31)&(lat<=64.51))[0]; ci=np.where((lon>=21.31)&(lon<=22.51))[0]
        sst=ds.analysed_sst.isel(time=0, latitude=ri, longitude=ci).values.astype(np.float64)
        np.savez(out, sst=sst, lat=lat[ri], lon=lon[ci], date=f'{d:%Y-%m-%d}')
    os.remove(raw)""","""    ok=False
    for attempt in range(5):
        try:
            if os.path.exists(raw): os.remove(raw)
            fs.get(f'{base}/sst_{d:%Y%m%d}.nc', raw)
            with xr.open_dataset(raw, engine='h5netcdf') as ds:
                lat=ds.latitude.values; lon=ds.longitude.values
                ri=np.where((lat>=63.31)&(lat<=64.51))[0]; ci=np.where((lon>=21.31)&(lon<=22.51))[0]
                sst=ds.analysed_sst.isel(time=0, latitude=ri, longitude=ci).values.astype(np.float64)
            np.savez(out, sst=sst, lat=lat[ri], lon=lon[ci], date=f'{d:%Y-%m-%d}')
            ok=True; break
        except Exception as e:
            print('retry',d,attempt,repr(e)[:200],flush=True); time.sleep(2)
    if os.path.exists(raw): os.remove(raw)
    if not ok: print('FAILED',d,flush=True)""")
s=s.replace("import fsspec, os,","import time, fsspec, os,")
open('/work/fetch.py','w').write(s)
subprocess.run('pkill -f fetch.py', shell=True)
subprocess.Popen('nohup python /work/fetch.py > /work/fetch.log 2>&1 &', shell=True)
time.sleep(90)
print(os.popen('ls /work/sub | wc -l; tail -5 /work/fetch.log').read())