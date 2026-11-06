import pickle, time
with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates = dd['base']; tgt_dates = dd['tgt']
all_dates = base_dates + tgt_dates

# import extract/process functions by re-running defs (stateless, uses fs/base globals)
exec(open('/dev/stdin').read()) if False else None
