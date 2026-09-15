from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


TARGET_CASES = {'GT_0005', 'GT_0006', 'GT_0007'}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def run(cmd: list[str]) -> None:
    print('> ' + ' '.join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description='Run NVT6 structure-ownership preflight for H1 control cases.')
    ap.add_argument('--ground-truth-dir', required=True)
    ap.add_argument('--resolved-cutoffs', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--lookback-bars', type=int, default=360)
    args = ap.parse_args()

    gt_dir = Path(args.ground_truth_dir)
    resolved = load_json(Path(args.resolved_cutoffs))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tool_dir = Path(__file__).resolve().parent

    gt_by_id = {}
    for path in gt_dir.glob('GT_*.json'):
        if path.name == 'GT_TEMPLATE.json':
            continue
        gt = load_json(path)
        cid = gt.get('case_id')
        if cid in TARGET_CASES:
            gt_by_id[cid] = (path, gt)

    missing = TARGET_CASES - set(gt_by_id)
    if missing:
        raise ValueError(f'missing Ground Truth cases: {sorted(missing)}')

    pair_for_case = {}
    for pair in resolved.get('pairs', []):
        case_ids = {x.strip() for x in str(pair.get('cases', '')).split(',') if x.strip()}
        for cid in TARGET_CASES & case_ids:
            pair_for_case[cid] = pair

    missing_pairs = TARGET_CASES - set(pair_for_case)
    if missing_pairs:
        raise ValueError(f'missing resolved cutoff pairs for: {sorted(missing_pairs)}')

    pool_by_pair = {}
    case_summaries = []

    for cid in sorted(TARGET_CASES):
        pair = pair_for_case[cid]
        source_id = str(pair['source_id'])
        tf = str(pair['timeframe'])
        if tf != 'H1':
            raise ValueError(f'{cid}: expected H1, got {tf}')
        pair_key = (source_id, tf)

        if pair_key not in pool_by_pair:
            pool_path = out_dir / f'{source_id}_{tf}_MICRO_DOW_POOL.json'
            run([
                sys.executable,
                str(tool_dir / 'build_micro_dow_pool.py'),
                '--input-csv', str(pair['input_csv']),
                '--cutoff', str(pair['exact_cutoff']),
                '--timeframe', tf,
                '--output', str(pool_path),
                '--lookback-bars', str(args.lookback_bars),
            ])
            pool_by_pair[pair_key] = pool_path

        gt_path, _ = gt_by_id[cid]
        evidence_path = out_dir / f'{cid}_STRUCTURE_OWNERSHIP_EVIDENCE.json'
        run([
            sys.executable,
            str(tool_dir / 'evaluate_structure_ownership.py'),
            '--ground-truth', str(gt_path),
            '--micro-pool', str(pool_by_pair[pair_key]),
            '--output', str(evidence_path),
        ])
        evidence = load_json(evidence_path)
        case_summaries.append({
            'case_id': cid,
            'source_id': source_id,
            'timeframe': tf,
            'exact_cutoff': pair['exact_cutoff'],
            'teacher_expectation': evidence['teacher_expectation'],
            'observation': evidence['observation'],
            'candidate_evidence': evidence['candidate_evidence'],
            'evidence_path': str(evidence_path),
        })

    by_case = {x['case_id']: x for x in case_summaries}
    gt5 = by_case['GT_0005']
    gt6 = by_case['GT_0006']
    gt7 = by_case['GT_0007']

    positive_recall = gt6['candidate_evidence']['p38_micro_count'] > 0
    gt7_global_no_line = (
        gt7['teacher_expectation']['no_line_scope'] == 'TIMEFRAME_GLOBAL'
    )
    gt7_candidates_present = gt7['candidate_evidence']['directional_candidate_count'] > 0
    gt5_structure_specific = (
        gt5['teacher_expectation']['no_line_scope'] == 'STRUCTURE_SPECIFIC'
    )

    summary = {
        'schema': 'nvt6-structure-ownership-preflight/0.2',
        'status': 'PASS',
        'mode': 'RESEARCH_ONLY',
        'cases': case_summaries,
        'preflight_findings': {
            'gt0006_p38_micro_recall_present': positive_recall,
            'gt0007_timeframe_global_no_line_evidence': gt7_global_no_line,
            'gt0007_candidates_still_present': gt7_candidates_present,
            'gt0005_structure_specific_no_line_evidence': gt5_structure_specific,
            'gt0005_rejected_structure_target_identification_required': gt5_structure_specific,
            'ownership_gate_required_before_selector': bool(
                positive_recall and (gt7_global_no_line or gt5_structure_specific)
            ),
        },
        'interpretation': (
            'GT_0007 may be used as a timeframe-global NO-LINE control. GT_0005 is '
            'structure-specific and must not label every other H1 candidate at the same '
            'cutoff as negative. Its rejected structure needs a separate target identity '
            'before candidate-level ownership scoring.'
        ),
        'production_writeback': False,
        'normal_run_modified': False,
        'mt4_object_writeback': False,
        'trade_authority': False,
    }
    summary_path = out_dir / 'NVT6_STRUCTURE_OWNERSHIP_PREFLIGHT_SUMMARY.json'
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'status': 'PASS',
        'summary': str(summary_path),
        **summary['preflight_findings'],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
