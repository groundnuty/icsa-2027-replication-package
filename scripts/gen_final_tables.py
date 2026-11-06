"""Write the final part's tables (markdown) from one seal, in the paper's shapes. T is "A".
Usage: python3 -I gen_final_tables.py <seal> [coded-dir]
"""
import csv, json, sys, os, math, collections, statistics as st
S = sys.argv[1]
CD = sys.argv[2] if len(sys.argv) > 2 else ('out-coded-kaug' if os.path.isdir(os.path.join(S, 'out-coded-kaug')) else 'out-coded')
T = os.path.join(S, CD, 'tables')
def J(*p):
    # in this package the coding data sit under results/coding/, beside results/analysis/<snapshot>/
    q = os.path.join(S, *p); alt = os.path.join(S, '..', '..', 'coding', *p)
    return q if os.path.exists(q) or not os.path.exists(alt) else alt
def rd(path):
    if not os.path.exists(path): return []
    L = open(path).read().splitlines(); return list(csv.DictReader(L[1:] if L and L[0].startswith('#') else L))
def fl(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def r2(x): return '' if x is None else f'{x:.2f}'
def r3(x): return '' if x is None else f'{x:.3f}'
def pp(x): return '' if x is None else f'{100*x:+.1f}'.replace('+-', '−').replace('-', '−')
def wilson(k, n, z=1.959964):
    if not n: return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h
NAME = {'T': 'A', 'D': 'D', 'M': 'M', 'T-unpaginated': 'A, complete listing'}
CN = lambda c: c.replace('T', 'A')
out = []
P = out.append
P(f'<!-- generated from {S} / {CD} -->')
lv = {(r['outcome'], r['option'], r['layout']): r for r in rd(os.path.join(T, 'levels.csv'))}
den = {(r['option'], r['layout']): r for r in rd(os.path.join(T, 'denominators.csv'))}
covf = {(r['option'], r['layout']): fl(r['mean']) for r in rd(J('layout', 'side', 'coverage_finished_levels.csv')) if r['outcome'] == 'coverage_target'}
_rp = J('h3', 'scored_rows_coded.jsonl')
if not os.path.exists(_rp) or os.path.getsize(_rp) == 0: _rp = os.path.join(S, CD, 'pipeline', 'scored_rows.jsonl')
rows = [json.loads(l) for l in open(_rp)]
m = [r for r in rows if r.get('block') in ('main', 'pagination')]
lab = lambda r: r.get('label_after_inspection') or r.get('label')
F = [r for r in m if r.get('finished')]
pag = {r['outcome']: r for r in rd(os.path.join(T, 'pagination_primary.csv'))}
# region mean for T-unpaginated (frozen averaging reproduced)
def region_mean(o, l, metric):
    d = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in F:
        if r['run']['option'] != o or r['run']['layout'] != l: continue
        if metric == 'omission':
            L = lab(r)
            if L not in ('omitting', 'complete'): continue
            v = 1.0 if L == 'omitting' else 0.0
        else:
            v = r.get('event_f1')
            if v is None: continue
        d[r['region_id']][r['run']['model']].append(v)
    g = [st.mean(st.mean(x) for x in M.values()) for M in d.values()]
    return st.mean(g) if g else None
rp = rd(J('coder_replay', 'coder_replay.csv')); num = fl
def disc(o, l):
    v = [r for r in rp if r['option'] == o and r['layout'] == l and r['replayed'] == 'true']
    om = [1 - num(r['cf_omission_f1']) for r in v if num(r['cf_omission_f1']) is not None]; co = [1 - num(r['cf_computation_f1']) for r in v if num(r['cf_computation_f1']) is not None]
    return (st.mean(om) if om else None, st.mean(co) if co else None)
cells = [('S1', 'T'), ('S1', 'D'), ('S1', 'M'), ('S1', 'T-unpaginated'), ('S2', 'T'), ('S2', 'D'), ('S2', 'M')]
P('\n### Completeness and correctness (Table VII)\n')
P('| Layout | Option | Runs | Omission, region mean [95%] | O/(O+C) [bounds] | Undisclosed | Coverage of target, all / finished | Event F1 [95%] | IoU ≥ 0.9 | End-to-end | Discrepancy: omission / computation |')
P('|---|---|---|---|---|---|---|---|---|---|---|')
for l, o in cells:
    d = den.get((o, l), {})
    om = lv.get(('omission', o, l)); f1 = lv.get(('event_f1', o, l)); ct = lv.get(('coverage_target', o, l))
    if om: omtxt = f"{r3(fl(om['mean']))} [{r3(fl(om['ci_lo']))}, {r3(fl(om['ci_hi']))}]"
    else: omtxt = f"{r3(region_mean(o, l, 'omission'))} (same averaging)"
    f1txt = f"{r3(fl(f1['mean']))} [{r3(fl(f1['ci_lo']))}, {r3(fl(f1['ci_hi']))}]" if f1 else f"{r3(region_mean(o, l, 'event_f1'))}"
    v = [r for r in F if r['run']['option'] == o and r['run']['layout'] == l]
    iou = [r['cell_day_iou'] for r in v if not r.get('event_free') and r.get('cell_day_iou') is not None]
    dm = disc(o, l)
    P(f"| {l} | {NAME[o]} | {d.get('N','')} | {omtxt} | {r2(fl(d.get('omission_rate')))} [{r2(fl(d.get('omission_lower')))}, {r2(fl(d.get('omission_upper')))}] | {r2(fl(d.get('undisclosed_rate')))} | {r2(fl(ct['mean'])) if ct else ''} / {r2(covf.get((o,l)))} | {f1txt} | {r2(sum(x >= .9 for x in iou)/len(iou)) if iou else ''} | {r2(fl(d.get('end_to_end_rate')))} | {r3(dm[0])} / {r3(dm[1])} |")
P('\n### Contrasts (Table VI): effect [95%], Holm p across the three pairs\n')
P('| Outcome | Layout | Contrast | Effect [95%] | Holm p |'); P('|---|---|---|---|---|')
for r in rd(os.path.join(T, 'contrasts.csv')):
    if r['outcome'] in ('omission', 'event_f1', 'coverage_target', 'tokens'):
        if r['outcome'] == 'tokens': eff = f"×{fl(r['effect_ratio']):.2f} [{fl(r['ci_lo_ratio']):.2f}, {fl(r['ci_hi_ratio']):.2f}]"
        elif r['outcome'] == 'event_f1': eff = f"{fl(r['effect']):+.3f} [{fl(r['ci_lo']):+.3f}, {fl(r['ci_hi']):+.3f}]"
        else: eff = f"{pp(fl(r['effect']))} pp [{pp(fl(r['ci_lo']))}, {pp(fl(r['ci_hi']))}]"
        P(f"| {r['outcome']} | {r['layout']} | {CN(r['contrast'])} | {eff} | {fl(r['p_holm']):.3f} |")
P('\n**Complete listing (A − A with complete listing, S1; single tests):**')
for k in ('omission', 'event_f1', 'coverage_target', 'tokens'):
    r = pag.get(k)
    if not r: continue
    if k == 'tokens':
        rr = fl(r['effect_ratio']); P(f"- tokens A / A-complete ×{1/rr:.2f} [{1/fl(r['ci_hi_ratio']):.2f}, {1/fl(r['ci_lo_ratio']):.2f}], p = {fl(r['p_raw']):.3f}")
    elif k == 'event_f1': P(f"- event F1 A − A-complete {-fl(r['effect']):+.3f} [{-fl(r['ci_hi']):+.3f}, {-fl(r['ci_lo']):+.3f}], p = {fl(r['p_raw']):.3f}")
    else: P(f"- {k} A − A-complete {pp(-fl(r['effect']))} pp [{pp(-fl(r['ci_hi']))}, {pp(-fl(r['ci_lo']))}], p = {fl(r['p_raw']):.3f}")
P('\n### Bytes between sites, the added test (measured units)\n')
found = False
for root, _, fs in os.walk(S):
    for fn in sorted(fs):
        if 'bytes' in fn and 'contrast' in fn and fn.endswith('.csv') and 'measured' in fn:
            found = True; P(f'from `{os.path.relpath(os.path.join(root, fn), S)}`:')
            for r in rd(os.path.join(root, fn)):
                try: P(f"- {r['layout']} {CN(r['contrast'])} ×{2**fl(r['effect']):.2f} [{2**fl(r['ci_lo']):.2f}, {2**fl(r['ci_hi']):.2f}], Holm p = {fl(r['p_holm']):.3f}")
                except Exception: pass
if not found: P('(no measured-units bytes-contrast file found in the seal)')
P('\n### Cost (Table VIII)\n')
env = {}
for r in rd(J('layout', 'layout_read.csv')): env[(r['block'], r['run'])] = r.get('environment')
cost = {(r['option'], r['layout']): r for r in rd(os.path.join(T, 'cost_table.csv'))}
P('| Layout | Option | Tokens, median (k) | Wall time, median, VM runs (min) | Bytes between sites, mean, VM runs (GB) |'); P('|---|---|---|---|---|')
for l, o in cells:
    walls = []
    for r in m:
        u = r['run']
        if u['option'] != o or u['layout'] != l or r.get('wall_time_s') is None: continue
        k = (r['block'], f"{u['instance_id']}__{u['option']}__{u['layout']}__{u['model']}__s{u['seed']}")
        if (env.get(k) == 'vm') if env else (r.get('bytes_between_sites') is not None): walls.append(r['wall_time_s'])
    c = cost.get((o, l), {})
    tok = fl(c.get('tokens_median')); by = fl(c.get('bytes_between_sites_mean'))
    P(f"| {l} | {NAME[o]} | {round(tok/1e3) if tok else ''} | {st.median(walls)/60:.1f} | {by/1e9:.2f} |" if walls and by is not None else f"| {l} | {NAME[o]} | {round(tok/1e3) if tok else ''} | {'%.1f' % (st.median(walls)/60) if walls else ''} | |")
P('\n### Validity\n')
k = rd(J('inspection', 'pair_kappa.csv')); R = [r for r in k if r['set'] == 'R+C']
n = sum(int(r['n']) for r in R); a = sum(int(r['agree']) for r in R); lo, hi = wilson(a, n)
P(f"- coder agreement {a} of {n} = {100*a/n:.1f}% [{100*lo:.1f}, {100*hi:.1f}] (Wilson)" if n else '- coder agreement: not available yet')
for lb in ('complete', 'omitting'):
    v = [r for r in rp if r['replayed'] == 'true' and r['label'] == lb and num(r['f1_extent']) is not None]
    kk = sum(num(r['f1_extent']) >= .99999 for r in v); lo, hi = wilson(kk, len(v))
    if not v: P(f'- replay, {lb}: not available yet'); continue
    P(f"- replay, {lb} labels matching exactly: {kk} of {len(v)} = {100*kk/len(v):.1f}% [{100*lo:.1f}, {100*hi:.1f}]")
kj = J('inspection', 'second_coder_kappa.json')
if os.path.exists(kj):
    d = json.load(open(kj)); e = d['first_reading']
    P(f"- second coder κ {e['all_rows']['kappa']:.2f} ({e['all_rows']['agree']} of {e['all_rows']['n']}); not by termination alone {e['not_decided_by_termination_alone']['kappa']:.2f}")
labs = json.load(open(os.path.join(T, 'manifest.json'))).get('label_sources') if os.path.exists(os.path.join(T, 'manifest.json')) else None
P(f"- labels: {labs}")
P('\n### Numbers in the text\n')
O = [r for r in F if lab(r) == 'omitting']
def sev(r):
    cb, ct = r.get('coverage_baseline'), r.get('coverage_target')
    if cb is None or ct is None: return 'unknown'
    return 'edge' if (ct >= .9999 and cb >= .99) else 'other'
P(f"- runs: {len(m)} scored, {len(F)} finished, {len({r['run']['model'] for r in m})} models")
P(f"- omitting: {len(O)} of {len(F)} finished ({100*len(O)/len(F):.1f}%); edge-day only {sum(sev(r)=='edge' for r in O)}; reported themselves complete {sum(1 for r in O if r.get('self_report_complete'))}")
P(f"- omitting by model: {collections.Counter(r['run']['model'] for r in O).most_common()}")
P(f"- token-budget endings by model: {collections.Counter(r['run']['model'] for r in m if r.get('termination')=='token_budget').most_common()}")
P(f"- time cap, D S2: {sum(1 for r in m if r.get('termination')=='time_cap' and r['run']['option']=='D' and r['run']['layout']=='S2')}")
for o in ('T', 'D', 'M', 'T-unpaginated'):
    v = [r for r in F if r['run']['option'] == o and lab(r) in ('complete', 'omitting') and r.get('self_report_complete') is not None]
    tp = sum(lab(r) == 'omitting' and not r['self_report_complete'] for r in v); fn = sum(lab(r) == 'omitting' and r['self_report_complete'] for r in v); fp = sum(lab(r) == 'complete' and not r['self_report_complete'] for r in v)
    P(f"- self-report {NAME[o]}: recall {tp/max(1,tp+fn):.2f}, precision {tp/(tp+fp):.2f}" if tp + fp else f"- self-report {NAME[o]}: recall {tp/max(1,tp+fn):.2f}, nothing flagged")
ef = [r for r in F if r.get('event_free')]
P(f"- false alarms on event-free instances: {sum(1 for r in ef if r.get('false_alarm'))} of {len(ef)}")
P('\n### Records in agent runs (registered, model-weighted)\n')
for name, path in (('as registered', J('h3', 'measure', 'record.csv')), ('own layout', J('layout', 'h3-own', 'measure', 'record.csv'))):
    for r in rd(path):
        if r['block'] == 'main' and r['model'] in ('*', '') and r['reading'] == 'primary' and r['variant'] == 'base' and r['metric'] == 'recall':
            pr = [x for x in rd(path) if x['block']=='main' and x['model'] in ('*','') and x['reading']=='primary' and x['variant']=='base' and x['metric']=='precision' and x['record']==r['record'] and x['option']==r['option'] and x['layout']==r['layout']]
            p = pr[0] if pr else {}
            P(f"- {name}: {r['record']} {NAME[r['option']]} {r['layout']}: {r['tp']}/{r['fp']}/{r['fn']}, recall {r2(fl(r['value']))} [{r2(fl(r['ci_lo']))}, {r2(fl(r['ci_hi']))}], precision {r2(fl(p.get('value')))}")
print('\n'.join(out))
