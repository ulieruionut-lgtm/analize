#!/usr/bin/env python3
"""
Test patient name extraction with improved cleaning.
Verifies that OCR garbage is properly removed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.parser import extract_nume


def test_patient_names():
    """Test various patient name extraction scenarios."""
    
    test_cases = [
        {
            "description": "Your screenshot case",
            "input": 'Nume: rii i "Laza Ana-Ramonaii 7.) ST on ete, srs',
            "expected_nume": "Laza Ana-Ramonai",
            "expected_has_prenume": True,
        },
        {
            "description": "Clean case",
            "input": "Nume: POPESCU IOAN",
            "expected_nume": "POPESCU",
            "expected_has_prenume": True,
        },
        {
            "description": "With garbage at end",
            "input": "Nume: IONESCU MARIA 7.) ST on ete",
            "expected_nume": "IONESCU",
            "expected_has_prenume": True,
        },
        {
            "description": "With leading garbage",
            "input": "Nume: pl COSTINESCU ANDREI",
            "expected_nume": "COSTINESCU",
            "expected_has_prenume": True,
        },
        {
            "description": "With CNP after",
            "input": "Nume: GEORGESCU ELENA CNP: 1234567890123",
            "expected_nume": "GEORGESCU",
            "expected_has_prenume": True,
        },
        {
            "description": "Hyphenated name",
            "input": "Nume: POPESCU-IONESCU ALEXANDRA",
            "expected_nume": "POPESCU-IONESCU",
            "expected_has_prenume": True,
        },
    ]
    
    print("=" * 80)
    print("🧪 PATIENT NAME EXTRACTION TESTS")
    print("=" * 80 + "\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['description']}")
        print(f"  Input:    {test['input'][:60]}")
        
        try:
            nume, prenume = extract_nume(test['input'])
            print(f"  ✓ Result:  {nume}")
            if prenume:
                print(f"           (prenume: {prenume})")
            
            # Verify
            if nume.upper() == test['expected_nume'].upper():
                print(f"  ✅ PASSED\n")
                passed += 1
            else:
                print(f"  ❌ FAILED (expected: {test['expected_nume']})\n")
                failed += 1
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            failed += 1
    
    print("=" * 80)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = test_patient_names()
    sys.exit(0 if success else 1)
