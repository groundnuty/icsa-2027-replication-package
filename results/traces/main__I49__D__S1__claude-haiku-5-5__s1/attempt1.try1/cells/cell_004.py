for pat in ['icsa2027_data_20261101T090944Z/s1z/sst_2019*','icsa2027_data_20261101T090944Z/s1z/sst_1992*','icsa2027_data_20261101T090944Z/s1z/sst_2003*']:
    try:
        g=fs.glob(pat); print(pat,len(g), g[:2])
    except Exception as e: print('err',e)
try:
    f=fs.find('icsa2027_data_20261101T090944Z/s1z'); print(len(f))
except Exception as e: print('find err',e)