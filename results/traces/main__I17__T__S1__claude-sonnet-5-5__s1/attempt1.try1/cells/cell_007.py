t=time.time()
with ThreadPoolExecutor(16) as ex: r=list(ex.map(get,ds))
print(time.time()-t,[x for x in r if x[1]!=True][:3],len(os.listdir('cache')))