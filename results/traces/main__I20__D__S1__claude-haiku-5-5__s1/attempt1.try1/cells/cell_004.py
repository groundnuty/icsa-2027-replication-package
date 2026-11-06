allf = fs.find('icsa2027_data_20261101T090944Z/s1z')
print(len(allf))
names = sorted(f.split('/')[-1] for f in allf if f.endswith('.nc'))
print(len(names), names[0], names[-1])
dates=set(re.findall(r'sst_(\d{8})\.nc',' '.join(names)))
miss=[x for x in need if x not in dates]
print(len(miss), miss[:5], miss[-5:])