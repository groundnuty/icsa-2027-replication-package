base='icsa2027_data_20261101T090944Z/s1z'
try:
    f=fs.find(base); print('find', len(f)); 
    print(collections.Counter(x.split('/')[-1][:4] for x in f).most_common(5))
    yrs=collections.Counter(re.search(r'(\d{4})\d{4}\.nc',x).group(1) for x in f if re.search(r'(\d{4})\d{4}\.nc',x)); print(sorted(yrs.items()))
except Exception as e: print('find err', e)
print(fs.info(base))