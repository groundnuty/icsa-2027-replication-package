ds=sorted(re.search(r'sst_(\d{8})',f).group(1) for f in fl if re.search(r'sst_\d{8}',f))
print(len(ds),ds[0],ds[-1])
S=set(ds);print([d for d in al if d not in S],[d for d in tg if d not in S])
print([f for f in fl if 'sst_' not in f])