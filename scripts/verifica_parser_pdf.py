#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificare parser PDF + benchmark set etalon (golden set).

Exemple:
  python scripts/verifica_parser_pdf.py "cale\\fisier.pdf"
  python scripts/verifica_parser_pdf.py "cale\\fisier.pdf" --json out.json
  python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.example.json --fail-below 0.9
  python scripts/verifica_parser_pdf.py --golden-dir tests/golden_set --fail-below 0.85
  python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.json --baseline scripts/golden_baseline.json
  python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.json --fail-below 0 --write-baseline scripts/golden_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _norm(s: str) -> str:
    t = (s or "").strip().lower()
    t = t.replace("\u0219", "s").replace("\u015f", "s").replace("\u021b", "t").replace("\u0163", "t")
    t = t.replace("\u0103", "a").replace("\u00e2", "a").replace("\u00ee", "i")
    t = "".join(ch for ch in unicodedata.normalize("NFD", t) if unicodedata.category(ch) != "Mn")
    return " ".join(t.split())


def _canonical_expected_item(item: dict) -> dict:
    """
    Acceptă atât cheile din proiect (denumire, valoare, unitate, categorie),
    cât și varianta propusă în documentație (analyte, value, unit, category).
    """
    if not isinstance(item, dict):
        return {}
    den = item.get("denumire") or item.get("denumire_raw") or item.get("analyte") or item.get("analit")
    val = item.get("valoare")
    if val is None and "value" in item:
        val = item.get("value")
    vtxt = item.get("valoare_text")
    if vtxt is None and item.get("value_text") is not None:
        vtxt = item.get("value_text")
    unit = item.get("unitate")
    if unit is None and item.get("unit") is not None:
        unit = item.get("unit")
    cat = item.get("categorie") or item.get("category")
    out = {}
    if den is not None:
        out["denumire"] = den
    if val is not None:
        out["valoare"] = val
    if vtxt is not None:
        out["valoare_text"] = vtxt
    if unit is not None:
        out["unitate"] = unit
    if cat is not None:
        out["categorie"] = cat
    return out


def _rezultat_key(item: dict, strict_values: bool) -> str:
    """Cheie comparare; în mod strict folosește denumire|valoare|unitate (fără categorie — parserul o are separat)."""
    if not isinstance(item, dict):
        return ""
    c = _canonical_expected_item(item)
    den = _norm(str(c.get("denumire") or ""))
    if not den:
        return ""
    if not strict_values:
        return den
    val = c.get("valoare")
    if val is None:
        val = _norm(str(c.get("valoare_text") or ""))
    else:
        val = str(val).strip()
    unit = _norm(str(c.get("unitate") or ""))
    return f"{den}|{val}|{unit}"


def _run_one_pdf(pdf: Path) -> dict:
    from backend.pdf_processor import extract_text_with_metrics
    from backend.parser import parse_full_text

    text, tip, err, _colored, extractor, ocr_metrics = extract_text_with_metrics(str(pdf))
    parsed = parse_full_text(text, cnp_optional=True) if text else None
    return {
        "text_len": len(text or ""),
        "tip": tip,
        "extractor": extractor,
        "ocr_err": err,
        "ocr_metrics": ocr_metrics,
        "parsed": parsed,
    }


def _print_single(parsed, meta: dict) -> None:
    print("Extragere:", meta.get("tip"), "| extractor:", meta.get("extractor"))
    print("Lungime text:", meta.get("text_len", 0))
    if meta.get("ocr_metrics"):
        print("OCR metrics:", json.dumps(meta["ocr_metrics"].get("summary", {}), ensure_ascii=False))
    if not parsed:
        print("Parser: None")
        return
    print("CNP:", parsed.cnp, "| Nume:", parsed.nume, parsed.prenume or "")
    print("Numar analize extrase:", len(parsed.rezultate))
    for i, r in enumerate(parsed.rezultate[:60], 1):
        v = r.valoare if r.valoare is not None else (r.valoare_text or "")
        cat = f" [{r.categorie}]" if r.categorie else ""
        den = (r.denumire_raw or "")[:55]
        rr = ",".join(getattr(r, "review_reasons", []) or [])
        rr_txt = f" !review({rr})" if rr else ""
        print(f"  {i:2}. {den}{cat} -> {v} {r.unitate or ''}{rr_txt}")
    if len(parsed.rezultate) > 60:
        print(f"  ... +{len(parsed.rezultate) - 60} altele")


def _load_cases_from_golden_json(golden_path: Path) -> list | None:
    if not golden_path.is_file():
        print("Fisier golden inexistent:", golden_path, file=sys.stderr)
        return None
    payload = json.loads(golden_path.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    if not isinstance(cases, list) or not cases:
        print("Golden set invalid: trebuie sa contina `cases`.", file=sys.stderr)
        return None
    return cases


def _load_cases_from_golden_dir(base: Path) -> list | None:
    """
    Structură recomandată (alternativă la un singur JSON manifest):
      tests/golden_set/input/*.pdf
      tests/golden_set/expected/<același_stem>.json  (listă sau {"expected": [...]})
    """
    inp = base / "input"
    exp = base / "expected"
    if not inp.is_dir():
        print("Golden dir: lipseste subfolder input/:", inp, file=sys.stderr)
        return None
    if not exp.is_dir():
        print("Golden dir: lipseste subfolder expected/:", exp, file=sys.stderr)
        return None
    cases: list = []
    for pdf in sorted(inp.glob("*.pdf")):
        try:
            rel_pdf = pdf.resolve().relative_to(ROOT)
        except ValueError:
            print(f"Golden dir: PDF in afara ROOT: {pdf}", file=sys.stderr)
            return None
        jf = exp / f"{pdf.stem}.json"
        if not jf.is_file():
            print(f"[golden-dir] skip (lipseste {jf.name} pentru {pdf.name})", file=sys.stderr)
            continue
        raw = json.loads(jf.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            expected = raw
        else:
            expected = raw.get("expected") or []
        if not isinstance(expected, list):
            print(f"[golden-dir] JSON invalid (nu e listă): {jf}", file=sys.stderr)
            return None
        cases.append({"pdf": str(rel_pdf).replace("\\", "/"), "expected": expected})
    if not cases:
        print("Golden dir: niciun PDF cu JSON pereche în expected/.", file=sys.stderr)
        return None
    return cases


def _run_golden(
    cases: list,
    strict_values: bool,
    fail_below: float,
    baseline_path: Path | None,
    write_baseline_path: Path | None,
) -> int:
    total_tp = total_fp = total_fn = 0
    total_review = 0
    total_extrase = 0
    for idx, case in enumerate(cases, 1):
        rel_pdf = case.get("pdf")
        if not rel_pdf:
            print(f"[case {idx}] lipseste `pdf`", file=sys.stderr)
            return 1
        pdf_path = (ROOT / rel_pdf).resolve()
        if not pdf_path.is_file():
            print(f"[case {idx}] PDF inexistent: {rel_pdf}", file=sys.stderr)
            return 1
        expected = case.get("expected") or []
        meta = _run_one_pdf(pdf_path)
        parsed = meta["parsed"]
        if not parsed:
            print(f"[case {idx}] parser None pentru: {rel_pdf}")
            total_fn += len(expected)
            continue

        got_items = [
            {
                "denumire_raw": r.denumire_raw,
                "valoare": r.valoare,
                "valoare_text": r.valoare_text,
                "unitate": r.unitate,
            }
            for r in parsed.rezultate
        ]
        got = {_rezultat_key(x, strict_values) for x in got_items if _rezultat_key(x, strict_values)}
        exp = {_rezultat_key(x, strict_values) for x in expected if _rezultat_key(x, strict_values)}
        tp = len(got & exp)
        fp = len(got - exp)
        fn = len(exp - got)
        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_extrase += len(parsed.rezultate)
        total_review += sum(1 for r in parsed.rezultate if getattr(r, "needs_review", False))
        p_c = tp / (tp + fp) if (tp + fp) else 0.0
        r_c = tp / (tp + fn) if (tp + fn) else 0.0
        f1_c = (2 * p_c * r_c / (p_c + r_c)) if (p_c + r_c) else 0.0
        print(
            f"[case {idx}] {rel_pdf} -> TP={tp} FP={fp} FN={fn} "
            f"extrase={len(parsed.rezultate)} F1_caz={f1_c:.4f}"
        )

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    review_rate = (total_review / total_extrase) if total_extrase else 0.0

    print("\n=== BENCHMARK GOLDEN ===")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")
    print(f"NeedsReviewRate: {review_rate:.4f} ({total_review}/{total_extrase})")

    if baseline_path and baseline_path.is_file():
        try:
            old = json.loads(baseline_path.read_text(encoding="utf-8"))
            of1 = float(old.get("f1", 0.0))
            if f1 + 1e-12 < of1:
                print(
                    f"FAIL: regresie fata de baseline F1 ({f1:.4f} < {of1:.4f} din {baseline_path})",
                    file=sys.stderr,
                )
                return 3
            print(f"OK vs baseline: F1 {f1:.4f} >= {of1:.4f} ({baseline_path.name})")
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Avertisment: baseline invalid ({e}), ignorat.", file=sys.stderr)

    if f1 < fail_below:
        print(f"FAIL: F1 ({f1:.4f}) < prag ({fail_below:.4f})", file=sys.stderr)
        return 2

    if write_baseline_path is not None:
        payload = {
            "f1": round(f1, 6),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "strict_values": strict_values,
            "cases": len(cases),
        }
        write_baseline_path.parent.mkdir(parents=True, exist_ok=True)
        write_baseline_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Baseline scris:", write_baseline_path.resolve())

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifica extragerea analizelor din PDF sau ruleaza benchmark pe set etalon.")
    ap.add_argument("pdf", type=Path, nargs="?", help="Calea catre fisierul PDF")
    ap.add_argument("--golden", type=Path, help="Fisier JSON manifest cu `cases` (vezi scripts/ocr_golden_set.example.json)")
    ap.add_argument(
        "--golden-dir",
        type=Path,
        help="Folder cu input/*.pdf și expected/<stem>.json (alternativ la --golden).",
    )
    ap.add_argument("--strict-values", action="store_true", help="Compara si valoare+unitate, nu doar denumirea.")
    ap.add_argument(
        "--fail-below",
        type=float,
        default=0.0,
        help="Ieșire cod 2 dacă F1 global < prag (ex: 0.9 producție, 0.8 MVP).",
    )
    ap.add_argument(
        "--baseline",
        type=Path,
        metavar="FISIER",
        help="Dacă fișierul există, eșuează (cod 3) când F1 nou < F1 din fișier (anti-regresie).",
    )
    ap.add_argument(
        "--write-baseline",
        type=Path,
        metavar="FISIER",
        help="După succes (F1 >= --fail-below), scrie F1/precision/recall în JSON pentru --baseline ulterior.",
    )
    ap.add_argument("--json", metavar="FISIER", type=Path, nargs="?", const=Path("-"))
    ap.add_argument("--list", metavar="FISIER", type=Path, nargs="?", const=Path("-"))
    args = ap.parse_args()

    if args.golden and args.golden_dir:
        print("Folositi fie --golden fie --golden-dir, nu ambele.", file=sys.stderr)
        return 1

    if args.golden_dir:
        cases = _load_cases_from_golden_dir(args.golden_dir.resolve())
        if cases is None:
            return 1
        return _run_golden(cases, args.strict_values, args.fail_below, args.baseline, args.write_baseline)

    if args.golden:
        cases = _load_cases_from_golden_json(args.golden)
        if cases is None:
            return 1
        return _run_golden(cases, args.strict_values, args.fail_below, args.baseline, args.write_baseline)

    if not args.pdf:
        ap.error("Trebuie sa specifici fie `pdf`, fie `--golden`.")
    pdf = args.pdf
    if not pdf.is_file():
        print("Fisier inexistent:", pdf, file=sys.stderr)
        return 1

    meta = _run_one_pdf(pdf)
    parsed = meta["parsed"]
    _print_single(parsed, meta)
    if not parsed:
        return 1

    if args.json is not None:
        out = parsed.model_dump(mode="json")
        payload = json.dumps(out, ensure_ascii=False, indent=2)
        if args.json == Path("-") or str(args.json) == "-":
            print(payload)
        else:
            args.json.write_text(payload, encoding="utf-8")
            print("JSON scris:", args.json.resolve())

    if args.list is not None:
        lines = []
        for r in parsed.rezultate:
            d = (r.denumire_raw or "").strip()
            if d:
                lines.append(d)
        body = "\n".join(lines) + ("\n" if lines else "")
        if args.list == Path("-") or str(args.list) == "-":
            sys.stdout.write(body)
        else:
            args.list.write_text(body, encoding="utf-8")
            print("Lista scrisa:", args.list.resolve(), f"({len(lines)} linii)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
