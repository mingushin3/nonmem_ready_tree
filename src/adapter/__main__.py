"""python -m src.adapter <xlsx_path> — Tier 0 adapter를 실물 파일에 실행(read-only 보고)."""
import json
import sys

from . import ingest


def _summarize(report: dict) -> str:
    fp = report["axis_fingerprint"]
    disp = report["dispatched"]
    lines = [
        f"source: {report['source']}",
        f"sheets: {[(s['name'], s['shape_class']) for s in report['sheets']]}",
        f"mess_profile(wired): {report['mess_profile']}",
        f"axis_fingerprint.resolved: {fp['resolved']}",
        f"axis_fingerprint.undetermined: {fp['undetermined']}",
        f"label: {fp['label']}",
        f"entry_node: {report['entry_node']}",
        f"dispatched.c_sequence: {disp['c_sequence']}",
        f"stop.at: {report['stop']['at']}  reason: {report['stop']['reason']}",
        f"reasons: {len(report['reasons'])}  decision_required: {len(report['decision_required'])}",
    ]
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m src.adapter <xlsx_path> [--json]", file=sys.stderr)
        return 2
    report = ingest(argv[0])
    if "--json" in argv:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(_summarize(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
