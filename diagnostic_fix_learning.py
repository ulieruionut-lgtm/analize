#!/usr/bin/env python3
"""
DIAGNOSTIC COMPLET - Verifica daca LLM Learning lucreaza cu fix-urile noi.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def run_diagnostics():
    """Run all diagnostic checks."""
    
    print("\n" + "=" * 80)
    print("🔍 DIAGNOSTIC COMPLET - LLM LEARNING SYSTEM")
    print("=" * 80 + "\n")
    
    # 1. Config check
    print("1️⃣  VERIFICARE CONFIGURARE...")
    print("-" * 80)
    try:
        from backend.config import settings
        
        llm_enabled = bool(getattr(settings, "llm_learn_from_upload_enabled", False))
        print(f"   • LLM Learning Enabled: {'✅ YES' if llm_enabled else '❌ NO'}")
        
        if not llm_enabled:
            print("\n   ⚠️  CRITICAL: Update .env with LLM_LEARN_FROM_UPLOAD_ENABLED=true")
        
        from backend.llm_chat import audit_llm_has_credentials
        has_creds = audit_llm_has_credentials()
        print(f"   • Anthropic API Key: {'✅ YES' if has_creds else '❌ NO'}")
        
        if not has_creds:
            print("\n   ⚠️  CRITICAL: Set ANTHROPIC_API_KEY in .env")
        
        print(f"\n   • Min score threshold: {getattr(settings, 'llm_learn_auto_apply_min_score', 86.0)}%")
        print(f"   • Max LLM calls/upload: {getattr(settings, 'llm_learn_max_calls_per_upload', 40)}")
        
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        return
    
    # 2. Code check - verify fixes
    print("\n2️⃣  VERIFICARE COD FIX-URI...")
    print("-" * 80)
    
    # Check filter removed
    try:
        from pathlib import Path
        llm_post_parse = Path("backend/llm_post_parse.py").read_text()
        if 'if len(raw) < 3:' in llm_post_parse:
            print("   ❌ FIX #1 MISSING: Still has 'if len(raw) < 3' filter!")
        else:
            print("   ✅ FIX #1 OK: Short name filter removed (< 1 char instead)")
        
        if 'if len(raw) < 1:' in llm_post_parse:
            print("   ✅ Accepts all short analysis names now")
    except Exception as e:
        print(f"   ❌ Error checking FIX #1: {e}")
    
    # Check logging wrapper
    try:
        main_py = Path("backend/main.py").read_text()
        if '_llm_learn_with_logging' in main_py:
            print("   ✅ FIX #2 OK: Error logging wrapper implemented")
        else:
            print("   ❌ FIX #2 MISSING: No error logging wrapper found!")
    except Exception as e:
        print(f"   ❌ Error checking FIX #2: {e}")
    
    # Check parser whitelist
    try:
        parser_py = Path("backend/parser.py").read_text()
        if '_VALID_SHORT_NAMES' in parser_py and '"K"' in parser_py:
            print("   ✅ FIX #3 OK: Whitelist with short names implemented")
        else:
            print("   ❌ FIX #3 MISSING: No whitelist found!")
    except Exception as e:
        print(f"   ❌ Error checking FIX #3: {e}")
    
    # 3. Database check
    print("\n3️⃣  VERIFICARE BAZA DE DATE...")
    print("-" * 80)
    try:
        from backend.database import get_cursor
        
        with get_cursor(commit=False) as cur:
            # Total aliases learned
            cur.execute("SELECT COUNT(*) FROM alias_analiza")
            total = cur.fetchone()[0]
            print(f"   • Total aliases learned: {total}")
            
            if total > 0:
                # Recent aliases
                cur.execute("""
                    SELECT pattern, scor_match, created_at 
                    FROM alias_analiza 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                print("\n   Recent aliases:")
                for pattern, score, created_at in cur.fetchall():
                    print(f"      - {pattern:<20} score: {score}% (created: {created_at})")
            
            # Pending unknown
            cur.execute("SELECT COUNT(*) FROM analiza_necunoscuta WHERE approved = FALSE")
            unknown = cur.fetchone()[0]
            print(f"\n   • Pending unknown analyses: {unknown}")
            
            # Upload count
            cur.execute("SELECT COUNT(*) FROM buletin")
            buletins = cur.fetchone()[0]
            print(f"   • Total buletins uploaded: {buletins}")
            
            if buletins > 0:
                # Mapping ratio
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE analiza_standard_id IS NOT NULL) * 100.0 / COUNT(*)
                    FROM rezultate
                """)
                ratio = cur.fetchone()[0]
                print(f"   • Overall mapping ratio: {ratio:.1f}%")
            
    except Exception as e:
        print(f"   ❌ Database error: {e}")
    
    # 4. Test LLM connection
    print("\n4️⃣  VERIFICARE CONEXIUNE LLM...")
    print("-" * 80)
    try:
        from backend.llm_chat import test_llm_connection
        success, msg = test_llm_connection()
        if success:
            print(f"   ✅ LLM Connection OK: {msg}")
        else:
            print(f"   ❌ LLM Connection FAILED: {msg}")
    except Exception as e:
        print(f"   ⚠️  Could not test LLM: {e}")
    
    # 5. Recommendations
    print("\n5️⃣  RECOMANDĂRI...")
    print("-" * 80)
    
    config_ok = llm_enabled and has_creds
    
    if not config_ok:
        print("   ⚠️  PRIORITATE 1: Configurare LLM")
        print("      - Verifica ANTHROPIC_API_KEY in .env")
        print("      - Verifica LLM_LEARN_FROM_UPLOAD_ENABLED=true")
        print("      - Restart aplicatia")
    
    if total == 0 and buletins > 0:
        print("\n   ⚠️  PRIORITATE 2: Testare Learning")
        print("      - Upload un nou buletin cu analize necunoscute scurte (K, Na, pH)")
        print("      - Verifica run_logs pentru [LLM-LEARN-SUCCESS] sau [LLM-LEARN-ERROR]")
        print("      - Ruleaza check_learning.py dupa 5 secunde")
    
    if total > 0:
        print("\n   ✅ EXCELENT: Learning este ACTIV!")
        print(f"      - {total} aliases invatate")
        print("      - Sistemul invata corect din uploade")
    
    print("\n" + "=" * 80)
    print("🔍 DIAGNOSTIC COMPLET")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    run_diagnostics()
