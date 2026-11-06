for s in ['19920101','20021231','20210601','20210831','19911227','20030105']:
    print(s,fs.exists(f'{p}/sst_{s}.nc'))
import inspect;print(type(fs))