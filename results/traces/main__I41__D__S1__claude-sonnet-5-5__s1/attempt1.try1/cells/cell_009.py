t0=time.time()
with ThreadPoolExecutor(8) as ex: res=list(ex.map(dl,days))
print(time.time()-t0,[r for r in res if r!=1][:3],len(glob.glob('/work/raw/*.nc')),len(days))