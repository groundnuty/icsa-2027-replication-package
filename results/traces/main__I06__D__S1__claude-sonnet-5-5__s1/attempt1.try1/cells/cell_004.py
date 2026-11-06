names=sorted(fs.find('icsa2027_data_20261101T090944Z/s1z'));print(len(names),names[-1])
ds=set(re.findall(r'(\d{8})',n)[-1] for n in names)
miss=[d for d in need if d not in ds];print(len(miss),miss[:50])