r=fs.find('icsa2027_data_20261101T090944Z/s1z');print(len(r))
try:
    r2=fs.ls('icsa2027_data_20261101T090944Z/s1z',detail=False);print(len(r2))
except Exception as e:print(e)
ds={re.findall(r'(\d{8})',n)[0] for n in r}
print(len(need-ds),sorted(need-ds)[:10],min(ds),max(ds))