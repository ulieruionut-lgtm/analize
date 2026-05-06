#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Diagnostic Upload & OCR
================================

Testează procesul complet de upload, OCR, și parsing.
Ajută la identificarea problemelor de recunoaștere.

Utilizare:
  python diagnostic_upload_ocr.py <path_to_pdf> --verbose
  python diagnostic_upload_ocr.py <path_to_pdf> --show-text
  python diagnostic_upload_ocr.py <path_to_pdf> --show-results
"""
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))

def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def diagnostic_pdf(pdf_path: str, verbose: bool = False, show_text: bool = False, show_results: bool = False):
    """Rulează diagnostic complet pe PDF."""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    if not pdf_file.suffix.lower() == '.pdf':
        print(f"❌ Not a PDF file: {pdf_path}")
        return
    
    print_section(f"DIAGNOSTIC UPLOAD & OCR: {pdf_file.name}")
    
    # 1. File Check
    print("📄 FILE INFORMATION")
    print(f"  Path: {pdf_file}")
    print(f"  Size: {pdf_file.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"  Exists: ✅")
    
    # 2. PDF Signature
    print("\n📋 PDF VALIDATION")
    content = pdf_file.read_bytes()
    
    def is_pdf_signature(content: bytes) -> bool:
        sample = (content or b"")[:16].lstrip()
        return sample.startswith(b"%PDF-")
    
    is_valid_pdf = is_pdf_signature(content)
    print(f"  PDF Signature: {'✅ Valid' if is_valid_pdf else '❌ Invalid'}")
    
    if not is_valid_pdf:
        print("  ⚠️  This is not a valid PDF. Check the file.")
        return
    
    # 3. OCR Extraction
    print("\n🔍 OCR EXTRACTION")
    try:
        from backend.pdf_processor import extract_text_with_metrics
        
        text, tip, ocr_err, colored_tokens, extractor, ocr_metrics = extract_text_with_metrics(pdf_path, dpi=None)
        
        print(f"  Type: {tip} ({'Embedded text' if tip == 'pdf_text' else 'Scanned (OCR)'})")
        print(f"  Extractor: {extractor}")
        print(f"  Text length: {len(text or '') } characters")
        
        if ocr_err:
            print(f"  ⚠️  OCR Error: {ocr_err}")
        
        # OCR Metrics
        if ocr_metrics and isinstance(ocr_metrics, dict):
            summary = ocr_metrics.get('summary', {})
            print(f"\n  OCR Metrics:")
            print(f"    - Avg Confidence: {summary.get('avg_mean_conf', 'N/A')}%")
            print(f"    - Weak Ratio: {summary.get('avg_weak_ratio', 'N/A')}")
            print(f"    - Total pages: {summary.get('total_pages', 'N/A')}")
        
        if show_text and text:
            print(f"\n  📝 EXTRACTED TEXT (first 1500 chars):")
            print(f"  {'-'*70}")
            print(text[:1500])
            if len(text) > 1500:
                print(f"  ... ({len(text) - 1500} more characters)")
        
    except Exception as e:
        print(f"  ❌ OCR Error: {str(e)[:200]}")
        return
    
    # 4. Parsing
    print("\n\n🔬 TEXT PARSING")
    try:
        from backend.parser import parse_full_text, extract_cnp, extract_nume, extract_rezultate
        
        cnp = extract_cnp(text or "")
        nome, prenume = extract_nume(text or "")
        rezultate = extract_rezultate(text or "")
        
        print(f"  CNP: {cnp or 'NOT FOUND'}")
        print(f"  Nome: {nome or 'NOT FOUND'}")
        print(f"  Prenume: {prenume or 'NOT FOUND'}")
        print(f"  Total results: {len(rezultate or [])}")
        
        if show_results and rezultate:
            print(f"\n  📊 EXTRACTED RESULTS:")
            for i, res in enumerate(rezultate[:20]):
                print(f"    {i+1}. {res.get('denumire_raw', '?')}")
                print(f"       Value: {res.get('valoare', '?')} {res.get('unitate', '')}")
                print(f"       Standard ID: {res.get('analiza_standard_id', 'NULL')}")
        
    except Exception as e:
        print(f"  ❌ Parsing Error: {str(e)[:200]}")
        return
    
    # 5. Normalization & Mapping
    print("\n\n🔗 NORMALIZATION & MAPPING")
    try:
        from backend.parser import parse_full_text
        from backend.normalizer import normalize_rezultate
        from backend.lab_detect import resolve_laborator_id_for_text
        
        parsed = parse_full_text(text or "", cnp_optional=True)
        if not parsed:
            print("  ❌ Could not parse patient")
            return
        
        lab_id, lab_name = resolve_laborator_id_for_text(text or "", pdf_file.name)
        normalize_rezultate(parsed.rezultate, laborator_id=lab_id)
        
        print(f"  Laboratory: {lab_name or 'Unknown'} (ID: {lab_id or 'NULL'})")
        
        # Count mappings
        mapped = sum(1 for r in parsed.rezultate if r.analiza_standard_id)
        unmapped = len(parsed.rezultate) - mapped
        
        print(f"  Mapped results: {mapped}/{len(parsed.rezultate)}")
        print(f"  Unmapped results: {unmapped}")
        print(f"  Mapping ratio: {100*mapped/max(len(parsed.rezultate), 1):.1f}%")
        
        if unmapped > 0 and show_results:
            print(f"\n  ⚠️  UNMAPPED RESULTS (candidates for LLM learning):")
            for i, res in enumerate(parsed.rezultate):
                if res.analiza_standard_id is None:
                    print(f"    - {res.denumire_raw}")
    
    except Exception as e:
        print(f"  ❌ Mapping Error: {str(e)[:200]}")
        return
    
    # 6. Quality Assessment
    print("\n\n📈 QUALITY ASSESSMENT")
    try:
        from backend.main import _calc_upload_quality, _calc_triage_ai
        
        quality = _calc_upload_quality(parsed)
        triage = _calc_triage_ai(parsed, tip, ocr_metrics)
        
        print(f"  Total analyses: {quality['total_rez']}")
        print(f"  Unknown mapping: {quality['nec']} ({100*quality['unknown_ratio']:.1f}%)")
        print(f"  Noise detected: {quality['zg']} ({100*quality['noise_ratio']:.1f}%)")
        print(f"  Unknown patient name: {quality['unknown_name']}")
        
        print(f"\n  AI Triage Score: {triage['score']}/100")
        print(f"  Decision: {triage['decision'].upper()}")
        print(f"  Reasons: {', '.join(triage['reasons']) if triage['reasons'] else 'N/A'}")
        
        # Warnings
        if triage['score'] < 20:
            print(f"\n  🔴 CRITICAL: Low quality. Requires review.")
        elif triage['score'] < 50:
            print(f"\n  🟡 WARNING: Medium quality. Consider review.")
        else:
            print(f"\n  ✅ OK: Good quality.")
    
    except Exception as e:
        print(f"  ❌ Quality Assessment Error: {str(e)[:200]}")
    
    # 7. LLM Learning Suggestions
    print("\n\n🤖 LLM LEARNING SUGGESTIONS")
    try:
        from backend.config import settings
        
        enabled = bool(getattr(settings, 'llm_learn_from_upload_enabled', False))
        print(f"  LLM Learning: {'✅ ENABLED' if enabled else '❌ DISABLED'}")
        
        if not enabled:
            print(f"\n  To enable auto-learning for unmapped analyses:")
            print(f"  1. Edit .env file")
            print(f"  2. Set: LLM_LEARN_FROM_UPLOAD_ENABLED=true")
            print(f"  3. Restart application")
        else:
            print(f"\n  This PDF will contribute to AI learning:")
            if unmapped > 0:
                print(f"  - {unmapped} new mappings will be learned from this upload")
            else:
                print(f"  - All analyses already known")
    
    except Exception as e:
        pass
    
    print("\n" + "="*70)
    print("  END OF DIAGNOSTIC")
    print("="*70 + "\n")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='PDF Upload & OCR Diagnostic')
    parser.add_argument('pdf_path', nargs='?', help='Path to PDF file to analyze')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--show-text', action='store_true', help='Show extracted text')
    parser.add_argument('--show-results', action='store_true', help='Show parsed results')
    
    args = parser.parse_args()
    
    if not args.pdf_path:
        print("Usage: python diagnostic_upload_ocr.py <pdf_file> [--verbose] [--show-text] [--show-results]")
        sys.exit(1)
    
    diagnostic_pdf(args.pdf_path, verbose=args.verbose, show_text=args.show_text, show_results=args.show_results)
