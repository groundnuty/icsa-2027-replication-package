"""Every number the final results part needs, from one sealed snapshot.

Usage: python3 -I final_numbers.py <final-dir> [coded-dir] [coded-rows.jsonl]
The per-run figures need the scored rows joined with the coders' labels (scored_rows_coded.jsonl).
Read-only. Prints sections; T is "A" in the paper.
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
    L = open(path).read().splitlines()
    return list(csv.DictReader(L[1:] if L and L[0].startswith('#') else L))
def f(x, n=3):
    try: return round(float(x), n)
    except (TypeError, ValueError): return None
def wilson(k, n, z=1.959964):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 4), round(c + h, 4)
def head(t): print('\n## ' + t)

print('# final numbers from', S, 'coded dir', CD)
print(open(os.path.join(T, 'contrasts.csv')).readline().strip())
man = json.load(open(os.path.join(T, 'manifest.json'))) if os.path.exists(os.path.join(T, 'manifest.json')) else {}
print('labels', man.get('label_sources'))

head('denominators (O/(O+C) and bounds, undisclosed, end-to-end, time-cap share)')
for r in rd(os.path.join(T, 'denominators.csv')):
    print(r['option'], r['layout'], 'N', r['N'], 'O', r['O'], 'C', r['C'], 'U', r['U'], 'K', r['K'], 'rate', f(r['omission_rate']), [f(r['omission_lower']), f(r['omission_upper'])], 'undiscl', f(r['undisclosed_rate']), 'e2e', f(r['end_to_end_rate']), 'tc', f(r.get('time_cap_share')))

head('levels: region means [95%]')
for r in rd(os.path.join(T, 'levels.csv')):
    if r['outcome'] in ('omission', 'coverage_target', 'coverage_baseline', 'event_f1'):
        print(r['outcome'], r['option'], r['layout'], f(r['mean']), [f(r['ci_lo']), f(r['ci_hi'])])
for r in rd(J('layout', 'side', 'coverage_finished_levels.csv')):
    if r['outcome'] == 'coverage_target': print('coverage_target finished', r['option'], r['layout'], f(r['mean']))

head('contrasts: effect [95%], Holm p, guide')
for r in rd(os.path.join(T, 'contrasts.csv')):
    if r['outcome'] in ('omission', 'event_f1', 'coverage_target', 'coverage_baseline', 'tokens'):
        ratio = f' ratio {f(r["effect_ratio"],2)} [{f(r["ci_lo_ratio"],2)}, {f(r["ci_hi_ratio"],2)}]' if r.get('effect_ratio') else ''
        print(f"{r['outcome']:17} {r['layout']} {r['contrast']:5} {f(r['effect'])} [{f(r['ci_lo'])}, {f(r['ci_hi'])}] pHolm {f(r['p_holm'],4)} sig {r['significant']} guide {r['counts_for_guide']}{ratio}")
head('complete listing: T-unpaginated minus T (single tests); A/A-complete tokens = 1/ratio')
for r in rd(os.path.join(T, 'pagination_primary.csv')):
    extra = ''
    if r.get('effect_ratio'):
        rr = float(r['effect_ratio']); extra = f" A/A-complete x{round(1/rr,2)} [{round(1/float(r['ci_hi_ratio']),2)}, {round(1/float(r['ci_lo_ratio']),2)}]"
    print(r['outcome'], f(r['effect']), [f(r['ci_lo']), f(r['ci_hi'])], 'p', f(r['p_raw'], 4), extra)

head('bytes: measured units (ratio = 2^effect) and the added test')
for r in rd(J('layout', 'bytes-measured', 'beside', 'h2_bytes.csv')):
    e = r['pooled_effect_measured_units']
    if e: print(r['layout'], r['contrast'], 'ratio', round(2 ** float(e), 2), [round(2 ** float(r['pooled_ci_lo_measured_units']), 2), round(2 ** float(r['pooled_ci_hi_measured_units']), 2)])
for root, _, fs in os.walk(S):
    for fn in fs:
        if fn.startswith('bytes-contrast') or (fn.startswith('bytes') and 'contrast' in fn and fn.endswith('.csv')):
            print('file', os.path.relpath(os.path.join(root, fn), S))
            for r in rd(os.path.join(root, fn)):
                try: print('  ', r['layout'], r['contrast'], 'ratio', round(2 ** float(r['effect']), 2), [round(2 ** float(r['ci_lo']), 2), round(2 ** float(r['ci_hi']), 2)], 'pHolm', f(r['p_holm'], 4))
                except Exception: pass

head('per-run measures from scored rows (finished runs, primary blocks)')
_rows = sys.argv[3] if len(sys.argv) > 3 else J('h3', 'scored_rows_coded.jsonl')
if not os.path.exists(_rows): sys.exit('per-run figures need the coded rows: pass their path as the third argument')
rows = [json.loads(l) for l in open(_rows)]
m = [r for r in rows if r.get('block') in ('main', 'pagination')]
lab = lambda r: r.get('label_after_inspection') or r.get('label')
F = [r for r in m if r.get('finished')]
print('scored', len(m), 'finished', len(F), 'models', len({r['run']['model'] for r in m}))
cells = [('T', 'S1'), ('D', 'S1'), ('M', 'S1'), ('T-unpaginated', 'S1'), ('T', 'S2'), ('D', 'S2'), ('M', 'S2')]
def sev(r):
    cb, ct = r.get('coverage_baseline'), r.get('coverage_target')
    if cb is None or ct is None: return 'unknown'
    if ct >= .9999 and cb >= .99: return 'edge'
    return 'other'
for o, l in cells:
    v = [r for r in F if r['run']['option'] == o and r['run']['layout'] == l]
    O = [r for r in v if lab(r) == 'omitting']; C = sum(lab(r) == 'complete' for r in v)
    edge = sum(sev(r) == 'edge' for r in O); other = len(O) - edge
    iou = [r['cell_day_iou'] for r in v if not r.get('event_free') and r.get('cell_day_iou') is not None]
    sr = [(lab(r), r['self_report_complete']) for r in v if lab(r) in ('complete', 'omitting') and r.get('self_report_complete') is not None]
    tp = sum(a == 'omitting' and not b for a, b in sr); fn = sum(a == 'omitting' and b for a, b in sr); fp = sum(a == 'complete' and not b for a, b in sr)
    ef = [r for r in v if r.get('event_free')]; fa = sum(1 for r in ef if r.get('false_alarm'))
    print(o, l, 'fin', len(v), 'O', len(O), 'edge-only', edge, 'without-edge', round(other / (other + C), 3) if other + C else None, 'IoU>=.9', round(sum(x >= .9 for x in iou) / len(iou), 3) if iou else None, 'self-report tp/fn/fp', tp, fn, fp, 'false alarms', fa, 'of', len(ef))
for o in ('T', 'D', 'M', 'T-unpaginated'):
    v = [r for r in F if r['run']['option'] == o and lab(r) in ('complete', 'omitting') and r.get('self_report_complete') is not None]
    tp = sum(lab(r) == 'omitting' and not r['self_report_complete'] for r in v); fn = sum(lab(r) == 'omitting' and r['self_report_complete'] for r in v); fp = sum(lab(r) == 'complete' and not r['self_report_complete'] for r in v)
    print('self-report pooled', o, 'recall', round(tp / max(1, tp + fn), 3), 'precision', round(tp / (tp + fp), 3) if tp + fp else None, tp, fn, fp)
Ofin = [r for r in F if lab(r) == 'omitting']
print('omitting', len(Ofin), 'of finished', len(F), round(len(Ofin) / len(F), 4), '| edge-only', sum(sev(r) == 'edge' for r in Ofin), '| null coverage', sum(sev(r) == 'unknown' for r in Ofin), '| reported complete', sum(1 for r in Ofin if r.get('self_report_complete')))
print('omitting by model', collections.Counter(r['run']['model'] for r in Ofin).most_common())
print('token budget by model', collections.Counter(r['run']['model'] for r in m if r.get('termination') == 'token_budget').most_common())
print('time cap by cell', collections.Counter((r['run']['option'], r['run']['layout']) for r in m if r.get('termination') == 'time_cap').most_common())

head('discrepancies and replay')
rp = rd(J('coder_replay', 'coder_replay.csv')); num = lambda x: float(x) if x not in ('', None) else None
for o, l in cells:
    v = [r for r in rp if r['option'] == o and r['layout'] == l and r['replayed'] == 'true']
    om = [1 - num(r['cf_omission_f1']) for r in v if num(r['cf_omission_f1']) is not None]; co = [1 - num(r['cf_computation_f1']) for r in v if num(r['cf_computation_f1']) is not None]
    if om: print('disc', o, l, len(om), round(st.mean(om), 4), round(st.mean(co), 4))
for lb in ('complete', 'omitting'):
    v = [r for r in rp if r['replayed'] == 'true' and r['label'] == lb and num(r['f1_extent']) is not None]
    k = sum(num(r['f1_extent']) >= .99999 for r in v); print('replay', lb, k, 'of', len(v), wilson(k, len(v)))

head('causes')
pc = rd(os.path.join(S, CD, 'pipeline', 'causes.csv')) or rd(J('out-coded', 'pipeline', 'causes.csv'))
cr = {r['run_key']: r for r in rd(J('coder_replay', 'coder_causes.csv'))}
key = lambda r: f"{r['block']}__{r['run']['instance_id']}__{r['run']['option']}__{r['run']['layout']}__{r['run']['model']}__s{r['run']['seed']}"
cc = {(c['block'], c['run_key']): c['cause'] for c in pc}
t = collections.Counter()
for r in Ofin:
    u = r['run']; k = key(r); short = f"{u['instance_id']}__{u['option']}__{u['layout']}__{u['model']}__s{u['seed']}"
    cause = (cr[k]['cause_window_rule'] or cr[k]['cause'] or 'not_coded') if k in cr else cc.get((r['block'], short), 'no_row')
    t[(u['option'], u['layout'], cause)] += 1
for o, l in cells: print('omitting', o, l, {k[2]: v for k, v in t.items() if k[0] == o and k[1] == l})
u2 = collections.Counter()
for c in pc:
    if c['population'] == 'unfinished' and c['block'] in ('main', 'pagination'):
        p = c['run_key'].split('__'); u2[(p[1], p[2], c['cause'])] += 1
for o, l in cells: print('unfinished', o, l, {k[2]: v for k, v in u2.items() if k[0] == o and k[1] == l})

head('coder agreement and second coder')
k = rd(J('inspection', 'pair_kappa.csv')); R = [r for r in k if r['set'] == 'R+C']
n = sum(int(r['n']) for r in R); a = sum(int(r['agree']) for r in R); print('pair agreement', a, n, round(a / n, 4) if n else None, wilson(a, n), 'pairs', sorted({r['coder_pair'] for r in R}))
for r in rd(J('inspection', 'second_coder_kappa.csv'))[:9]: print('kappa', r)

head('records in agent runs (registered model-weighted values, counts summed)')
for name, path in (('registered', J('h3', 'measure', 'record.csv')), ('own-layout', J('layout', 'h3-own', 'measure', 'record.csv'))):
    for r in rd(path):
        if r['block'] == 'main' and r['model'] in ('*', '') and r['reading'] == 'primary' and r['variant'] == 'base' and r['metric'] in ('recall', 'precision'):
            print(name, r['record'], r['option'], r['layout'], r['metric'], f(r['value'], 2), [f(r['ci_lo'], 2), f(r['ci_hi'], 2)], 'tp/fp/fn', r['tp'], r['fp'], r['fn'], r['status'])

head('fault injection per fault type')
for r in rd(J('exhibits', 'fidelity_per_fault_type.csv')):
    if r['fault_in_tested_subset'] in ('yes', 'per_instance'):
        print(r['fault_type'], r['option'], r['layout'], r['record'], r['condition'], 'recall', f(r['recall'], 2), 'precision', f(r['precision'], 2), 'n', r['n_faulted'], '/', r['n_control'], r['cell_status'])

head('side files present')
for root, _, fs in os.walk(S):
    for fn in fs:
        if any(s in fn for s in ('overhead', 'extent_account', 'records_table', 'fidelity_split', 'exhausted_sensitivity', 'lab504', 'retries')) and fn.endswith(('.csv', '.json')):
            print(os.path.relpath(os.path.join(root, fn), S))
