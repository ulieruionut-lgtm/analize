#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Verificare și Activare LLM Learning
==========================================

Verifică configurația LLM și salvează alias-uri în DB.
Folost pentru diagnostic și testare.

Utilizare:
  python check_llm_learning.py --status
  python check_llm_learning.py --enable
  python check_llm_learning.py --test-llm-call
  python check_llm_learning.py --import-sample-aliases
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

# Adaugă backend la path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_section(title: str):
    """Print section header."""
    print(f"\n📌 {title}\n" + "─"*70)

def check_env_vars() -> Dict[str, Optional[str]]:
    """Verifică variabilele de mediu critice."""
    vars_to_check = {
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'LLM_API_KEY': os.getenv('LLM_API_KEY'),
        'LLM_PROVIDER': os.getenv('LLM_PROVIDER', 'openai'),
        'LLM_MODEL': os.getenv('LLM_MODEL', 'not-set'),
        'DATABASE_URL': os.getenv('DATABASE_URL', 'not-set')[:30] + '...',
    }
    return vars_to_check

def check_config_file() -> Dict[str, bool]:
    """Verifică fișierul .env și config.py."""
    env_file = Path('.env')
    config_file = Path('backend/config.py')
    
    return {
        '.env exists': env_file.exists(),
        'config.py exists': config_file.exists(),
    }

def get_settings() -> Optional[Any]:
    """Încarcă settings din backend."""
    try:
        from backend.config import settings
        return settings
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return None

def check_llm_learning_config() -> Dict[str, Any]:
    """Verifică configurația LLM Learning."""
    settings = get_settings()
    if not settings:
        return {'error': 'Could not load settings'}
    
    return {
        'llm_learn_from_upload_enabled': bool(getattr(settings, 'llm_learn_from_upload_enabled', False)),
        'llm_buletin_audit_enabled': bool(getattr(settings, 'llm_buletin_audit_enabled', False)),
        'llm_learn_auto_apply_min_score': float(getattr(settings, 'llm_learn_auto_apply_min_score', 86.0)),
        'llm_learn_max_calls_per_upload': int(getattr(settings, 'llm_learn_max_calls_per_upload', 40)),
    }

def check_database() -> Dict[str, Any]:
    """Verifică tabelele database."""
    try:
        from backend.database import get_cursor
        
        stats = {}
        table_names = [
            'analize_standard',
            'alias_analiza',
            'analiza_necunoscuta',
            'catalog_laborator'
        ]
        
        for table in table_names:
            try:
                with get_cursor(commit=False) as cur:
                    cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    row = cur.fetchone()
                    count = row[0] if isinstance(row, (tuple, list)) else row.get('cnt', 0)
                    stats[table] = count
            except Exception as e:
                stats[table] = f"Error: {str(e)[:50]}"
        
        return stats
    except Exception as e:
        return {'error': f"DB connection failed: {str(e)[:100]}"}

def test_llm_call() -> Dict[str, Any]:
    """Test apel LLM Haiku."""
    try:
        from backend.llm_chat import (
            chat_completion_system_user,
            audit_llm_has_credentials,
            llm_provider_normalized,
            resolve_model_name
        )
        
        if not audit_llm_has_credentials():
            return {'status': 'error', 'message': 'No LLM credentials configured'}
        
        provider = llm_provider_normalized()
        model = resolve_model_name()
        
        print(f"🤖 Testing LLM call...")
        print(f"   Provider: {provider}")
        print(f"   Model: {model}")
        
        # Test call
        response = chat_completion_system_user(
            system="Ești ajutor medical. Răspunde scurt în JSON.",
            user='{"test": "activation"}',
            max_tokens=100,
            temperature=0.0
        )
        
        return {
            'status': 'success',
            'provider': provider,
            'model': model,
            'response_length': len(response),
            'first_100_chars': response[:100]
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)[:200]
        }

def enable_llm_learning():
    """Activează LLM Learning în .env."""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    content = env_file.read_text(encoding='utf-8')
    
    # Verifică dacă e deja setat
    if 'LLM_LEARN_FROM_UPLOAD_ENABLED=true' in content:
        print("✅ LLM Learning already enabled")
        return True
    
    # Înlocuiește false cu true
    new_content = content.replace(
        'LLM_LEARN_FROM_UPLOAD_ENABLED=false',
        'LLM_LEARN_FROM_UPLOAD_ENABLED=true'
    )
    
    # Dacă nu e în fișier, adaugă
    if 'LLM_LEARN_FROM_UPLOAD_ENABLED=' not in new_content:
        new_content += '\nLLM_LEARN_FROM_UPLOAD_ENABLED=true\n'
    
    env_file.write_text(new_content, encoding='utf-8')
    print("✅ LLM Learning ENABLED in .env")
    return True

def import_sample_aliases():
    """Importează alias-uri de test."""
    try:
        from backend.database import get_cursor, get_all_analize_standard
        
        # Sample aliases
        sample_aliases = {
            'VSH': 'VSH Viteza Sedimentare Hematii',
            'TGO': 'ASAT (Aspartat Aminotransferaz)',
            'TGP': 'ALAT (Alaninamino transferaz)',
            'Leuc': 'Leucocite',
            'Eritro': 'Eritrocite',
            'Hb': 'Hemoglobina',
            'Tc': 'Trombocite',
        }
        
        # Găsește IDs
        catalog = get_all_analize_standard() or []
        catalog_map = {a['denumire_standard']: a['id'] for a in catalog}
        
        imported = 0
        failed = []
        
        for pattern, standard_name in sample_aliases.items():
            standard_id = catalog_map.get(standard_name)
            if not standard_id:
                failed.append(f"{pattern} → {standard_name} (not in catalog)")
                continue
            
            try:
                with get_cursor(commit=True) as cur:
                    # Simplu: insert în alias_analiza
                    sql = """
                    INSERT INTO alias_analiza (pattern, analiza_standard_id, scor_match)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (pattern) DO UPDATE SET scor_match = 99.0
                    """
                    cur.execute(sql, (pattern, standard_id, 99.0))
                imported += 1
                print(f"  ✅ {pattern} → {standard_name} (ID: {standard_id})")
            except Exception as e:
                failed.append(f"{pattern}: {str(e)[:80]}")
        
        print(f"\n✅ Imported {imported} aliases")
        if failed:
            print(f"❌ Failed {len(failed)}:")
            for f in failed:
                print(f"   - {f}")
        
        return imported > 0
    
    except Exception as e:
        print(f"❌ Error importing aliases: {e}")
        return False

def status_report():
    """Raport complet status."""
    print_header("LLM LEARNING STATUS REPORT")
    
    # 1. Config Files
    print_section("1. Config Files")
    config_check = check_config_file()
    for key, val in config_check.items():
        status = "✅" if val else "❌"
        print(f"{status} {key}: {val}")
    
    # 2. Environment Variables
    print_section("2. Environment Variables")
    env_vars = check_env_vars()
    for key, val in env_vars.items():
        if val and len(str(val)) > 3:
            print(f"✅ {key}: {val}")
        else:
            print(f"❌ {key}: NOT SET")
    
    # 3. LLM Learning Config
    print_section("3. LLM Learning Configuration")
    llm_config = check_llm_learning_config()
    if 'error' in llm_config:
        print(f"❌ {llm_config['error']}")
    else:
        for key, val in llm_config.items():
            status = "✅" if val else "⚠️"
            print(f"{status} {key}: {val}")
    
    # 4. Database Tables
    print_section("4. Database Tables")
    db_stats = check_database()
    if 'error' in db_stats:
        print(f"❌ {db_stats['error']}")
    else:
        for table, count in db_stats.items():
            if isinstance(count, int):
                print(f"📊 {table}: {count} rows")
            else:
                print(f"❌ {table}: {count}")
    
    # 5. LLM Credentials
    print_section("5. LLM Credentials Test")
    llm_test = test_llm_call()
    print(f"Status: {llm_test.get('status', '?')}")
    if llm_test.get('status') == 'success':
        print(f"✅ Provider: {llm_test.get('provider')}")
        print(f"✅ Model: {llm_test.get('model')}")
    else:
        print(f"❌ Error: {llm_test.get('message', 'Unknown')}")
    
    print_header("END OF REPORT")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM Learning Configuration')
    parser.add_argument('--status', action='store_true', help='Show status report')
    parser.add_argument('--enable', action='store_true', help='Enable LLM learning in .env')
    parser.add_argument('--test-llm-call', action='store_true', help='Test LLM API call')
    parser.add_argument('--import-sample-aliases', action='store_true', help='Import sample aliases')
    
    args = parser.parse_args()
    
    if args.status:
        status_report()
    elif args.enable:
        enable_llm_learning()
    elif args.test_llm_call:
        print_section("Testing LLM Call")
        result = test_llm_call()
        print(json.dumps(result, indent=2))
    elif args.import_sample_aliases:
        print_section("Importing Sample Aliases")
        import_sample_aliases()
    else:
        # Default: show status
        status_report()
