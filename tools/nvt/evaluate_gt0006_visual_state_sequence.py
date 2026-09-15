from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Evaluate multiple GT_0006 visual line-value samples against Gate-C candidate geometries.'
    )
    ap.add_argument('--gate-report', required=True)
    ap.add_argument('--evidence', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    gate = load_json(args.gate_report)
    evidence = load_json(args.evidence)

    case = (gate.get('cases') or {}).get('GT_0006')
    if not case:
        raise ValueError('GT_0006 missing from gate report')

    candidates = [c for c in case.get('candidates', []) if c.get('gate_C_A_and_B') is True]
    if not candidates:
        raise ValueError('no GT_0006 Gate-C candidates')

    a1 = evidence['common_candidate_anchor1_assumption']
    a1_time = parse_dt(a1['time'])
    a1_price = float(a1['price'])

    observation_results = []
    for obs in evidence.get('observations', []):
        sample_time = parse_dt(obs['chart_status_time'])
        elapsed_hours = (sample_time - a1_time).total_seconds() / 3600.0
        observed = float(obs['tooltip_line_value'])
        tol = float(obs['match_tolerance'])

        ranked = []
        for c in candidates:
            slope = float(c['absolute_slope_per_hour'])
            predicted = a1_price - slope * elapsed_hours
            err = abs(predicted - observed)
            ranked.append({
                'candidate_key': c.get('candidate_key'),
                'anchor2_time': c.get('anchor2_time'),
                'anchor2_price': c.get('anchor2_price'),
                'absolute_slope_per_hour': slope,
                'predicted_line_value': predicted,
                'absolute_error': err,
                'within_tolerance': err <= tol,
            })
        ranked.sort(key=lambda r: (r['absolute_error'], r['candidate_key'] or ''))
        within = [r for r in ranked if r['within_tolerance']]
        observation_results.append({
            **obs,
            'elapsed_hours_from_common_anchor1': elapsed_hours,
            'within_tolerance_count': len(within),
            'within_tolerance_candidates': within,
            'top5_by_error': ranked[:5],
            'best_match': ranked[0],
        })

    # Test whether one fixed candidate can explain every direct sample under each sample's tolerance.
    compatible_all = []
    for c in candidates:
        ok = True
        per_obs = []
        for r in observation_results:
            hit = next(x for x in r['top5_by_error'] + r['within_tolerance_candidates'] if x['candidate_key'] == c['candidate_key']) if any(
                x['candidate_key'] == c['candidate_key'] for x in r['top5_by_error'] + r['within_tolerance_candidates']
            ) else None
            if hit is None:
                sample_time = parse_dt(r['chart_status_time'])
                elapsed_hours = (sample_time - a1_time).total_seconds() / 3600.0
                predicted = a1_price - float(c['absolute_slope_per_hour']) * elapsed_hours
                err = abs(predicted - float(r['tooltip_line_value']))
                hit = {
                    'candidate_key': c.get('candidate_key'),
                    'anchor2_time': c.get('anchor2_time'),
                    'anchor2_price': c.get('anchor2_price'),
                    'predicted_line_value': predicted,
                    'absolute_error': err,
                    'within_tolerance': err <= float(r['match_tolerance']),
                }
            per_obs.append({'observation_id': r['id'], **hit})
            if not hit['within_tolerance']:
                ok = False
        if ok:
            compatible_all.append({
                'candidate_key': c.get('candidate_key'),
                'anchor2_time': c.get('anchor2_time'),
                'anchor2_price': c.get('anchor2_price'),
                'per_observation': per_obs,
            })

    by_id = {r['id']: r for r in observation_results}
    v1 = by_id.get('V1_GENTLE_FAMILY')
    v3 = by_id.get('V3_STEEPER_STATE')
    v4 = by_id.get('V4_LATER_HIGH_REANCHOR_STATE')

    report = {
        'schema': 'nvt6-gt0006-visual-state-sequence/0.1',
        'status': 'RESEARCH_ONLY',
        'case_id': 'GT_0006',
        'source': evidence.get('source'),
        'common_candidate_anchor1_assumption': a1,
        'input_gate_c_candidate_count': len(candidates),
        'observation_results': observation_results,
        'single_fixed_geometry_test': {
            'candidate_count_fitting_all_samples': len(compatible_all),
            'candidates_fitting_all_samples': compatible_all,
            'supports_state_change_or_transient_edit': len(compatible_all) == 0,
            'guard': (
                'Failure of one fixed common-anchor1 candidate to fit all samples is evidence for '
                'geometry-state change/transient editing only in combination with the video context; '
                'it must not be interpreted as a production lifecycle rule by itself.'
            ),
        },
        'research_findings': {
            'v1_late_gentle_family_count': None if not v1 else v1['within_tolerance_count'],
            'v3_best_anchor2_time': None if not v3 else v3['best_match']['anchor2_time'],
            'v3_best_error': None if not v3 else v3['best_match']['absolute_error'],
            'v4_best_anchor2_time': None if not v4 else v4['best_match']['anchor2_time'],
            'v4_best_error': None if not v4 else v4['best_match']['absolute_error'],
            'same_mt4_object_name_observed_across_sequence': True,
            'selector_lifecycle_boundary_material': True,
        },
        'recommended_handoff': {
            'NVT6': [
                'Preserve ownership Gate-C as research hypothesis only.',
                'Treat cluster-right-edge candidates as valid alternatives before final preference.',
                'Do not hard-lock GT_0006 to the V1 unique cross-feature lead from a single static sample.',
            ],
            'NVT7': [
                'Model same-object re-anchor/update states explicitly.',
                'Test later-high replacement/re-anchor without deleting still-useful reference structures by default.',
                'Separate transient drag/edit samples from stable post-edit geometry states.',
            ],
        },
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': 'PASS',
        'output': str(out),
        'gate_c_candidate_count': len(candidates),
        'single_fixed_geometry_fit_count': len(compatible_all),
        'v1_within_tolerance_count': report['research_findings']['v1_late_gentle_family_count'],
        'v3_best_anchor2_time': report['research_findings']['v3_best_anchor2_time'],
        'v4_best_anchor2_time': report['research_findings']['v4_best_anchor2_time'],
        'selector_lifecycle_boundary_material': True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
