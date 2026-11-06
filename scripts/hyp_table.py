"""Provisional or final hypothesis verdicts from one sealed snapshot, by the registered decision rules.

Usage: python3 -I hyp_table.py <seal> [analysis-dir, default out-coded]
A difference counts for the decision guide only if Holm-significant and at least the smallest effect
(10 points for omission or coverage, a factor of 2 for cost). H3 passes a record x option x layout when both
point estimates are >= 0.9 on the tested subset. H4: model directions from h4_directions.
"""
import csv, json, sys, os, math

seal = sys.argv[1]; sub = sys.argv[2] if len(sys.argv) > 2 else 'out-coded'
T = os.path.join(seal, sub, 'tables')

def rd(path):
    if not os.path.exists(path): return []
    L = open(path).read().splitlines()
    return list(csv.DictReader(L[1:] if L and L[0].startswith('#') else L))

def f(x, n=3):
    try: return round(float(x), n)
    except (TypeError, ValueError): return None

def yes(x): return str(x).strip().lower() in ('1', '1.0', 'true', 'yes')

print('# Hypothesis verdicts from', seal, sub)
stamp = open(os.path.join(T, 'contrasts.csv')).readline().strip(); print(stamp)

print('\n## H1, H2 tokens: option contrasts (effect [95% CI], Holm p, counts for guide)')
for r in rd(os.path.join(T, 'contrasts.csv')):
    if r['outcome'] in ('omission', 'event_f1', 'coverage_target', 'coverage_baseline', 'tokens'):
        ratio = f'  ratio {f(r["effect_ratio"],2)} [{f(r["ci_lo_ratio"],2)}, {f(r["ci_hi_ratio"],2)}]' if r.get('effect_ratio') else ''
        print(f"{r['outcome']:18} {r['layout']} {r['contrast']:5} {f(r['effect']):>7} [{f(r['ci_lo'])}, {f(r['ci_hi'])}]  pHolm {f(r['p_holm'])}  sig {yes(r['significant'])}  >=smallest {yes(r['at_least_smallest'])}  guide {yes(r['counts_for_guide'])}{ratio}  regions {r['n_regions']}")

print('\n## H1 mechanism: T with a complete listing minus T, S1')
for r in rd(os.path.join(T, 'pagination_primary.csv')):
    print(f"{r['outcome']:18} {f(r['effect']):>7} [{f(r['ci_lo'])}, {f(r['ci_hi'])}]  p {f(r['p_raw'])}  >=smallest {yes(r['at_least_smallest'])}")

print('\n## H2 bytes between sites, measured units (beside, VM runs)')
for r in rd(os.path.join(seal, 'layout/bytes-measured/beside/h2_bytes.csv')):
    print(f"{r['layout']} {r['contrast']:5} primary ratio {f(r['pooled_effect_ratio_primary'],2)} [{f(2**float(r['pooled_ci_lo_primary']),2) if r['pooled_ci_lo_primary'] else None}, {f(2**float(r['pooled_ci_hi_primary']),2) if r['pooled_ci_hi_primary'] else None}] models agreeing {r['n_models_agreeing_primary']}/{r['n_models_primary']} | measured-units ratio {f(r['pooled_effect_ratio_measured_units'],2)} [{f(2**float(r['pooled_ci_lo_measured_units']),2) if r['pooled_ci_lo_measured_units'] else None}, {f(2**float(r['pooled_ci_hi_measured_units']),2) if r['pooled_ci_hi_measured_units'] else None}]")
bu = os.path.join(seal, 'layout/bytes_units.json')
if os.path.exists(bu): print('units', json.load(open(bu)))

print('\n## H2 wall time, medians as measured (s)')
for r in rd(os.path.join(T, 'wall_time_contrasts_with_overhead.csv')):
    print(r['layout'], r['contrast'], r['wall_time_s_median_a'][:7], r['wall_time_s_median_b'][:7], r['difference_as_measured_s'][:8], r['overhead_status_a'], r['overhead_status_b'])

print('\n## H3 fault injection: tested cells, recall/precision, meets 0.9')
for r in rd(os.path.join(T, 'fault_injection_fidelity.csv')):
    if r['condition'] in ('cold', '') or True:
        print(f"{r['option']} {r['layout']} {r['record']:9} {r['condition']:6} {r['subset']:10} tested {r['tested']:5} n {r['n_faulted']:>3}/{r['n_control']:>3} recall {f(r['recall'],2)} [{f(r['recall_lo'],2)}] prec {f(r['precision'],2)} [{f(r['precision_lo'],2)}] status {r['status']} meets {r['meets_h3']}")

print('\n## H4: directions across models')
for r in rd(os.path.join(T, 'h4_directions.csv')):
    print(f"{r['outcome']:12} {r['layout']} {r['contrast']:5} pooled {f(r['pooled_effect'])} dir {r['pooled_direction']:8} agreeing {r['n_models_agreeing']}/{r['n_models']} | cheaper {r['cheaper_model'][:12]} {f(r['cheaper_effect'])} agrees {r['cheaper_agrees_with_pooled']} | stronger {r['stronger_model'][:12]} {f(r['stronger_effect'])} agrees {r['stronger_agrees_with_pooled']}")
