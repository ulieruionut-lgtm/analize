#!/usr/bin/env python3
"""Verify if LLM learning is actually happening."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def check_database():
    """Check actual DB content."""
    try:
        from backend.database import get_cursor
        
        print("=" * 70)
        print("DATABASE LEARNING STATUS CHECK")
        print("=" * 70 + "\n")
        
        with get_cursor(commit=False) as cur:
            # 1. Total aliases
            cur.execute("SELECT COUNT(*) FROM alias_analiza")
            total = cur.fetchone()[0]
            print(f"📊 Total aliases learned: {total}")
            
            # 2. Recent aliases
            if total > 0:
                print("\n📈 Recent aliases (last 5):")
                cur.execute("""
                    SELECT pattern, scor_match, created_at 
                    FROM alias_analiza 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                for pattern, score, created_at in cur.fetchall():
                    print(f"   - {pattern:<20} score: {score}% (created: {created_at})")
            else:
                print("\n   ⚠️  NO aliases learned yet!")
            
            # 3. Pending unknown
            cur.execute("SELECT COUNT(*) FROM analiza_necunoscuta WHERE approved = FALSE")
            unknown = cur.fetchone()[0]
            print(f"\n⏳ Pending unknown analyses: {unknown}")
            
            if unknown > 0:
                print("\n   Sample unknown (first 5):")
                cur.execute("""
                    SELECT DISTINCT laborator_id, denumire_raw 
                    FROM analiza_necunoscuta 
                    WHERE approved = FALSE 
                    LIMIT 5
                """)
                for lab_id, name in cur.fetchall():
                    print(f"   - {name} (lab: {lab_id})")
            
            # 4. Check buletins uploaded
            cur.execute("SELECT COUNT(*) FROM buletin")
            buletins = cur.fetchone()[0]
            print(f"\n📋 Total buletins uploaded: {buletins}")
            
            # 5. Check mapping ratio
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE analiza_standard_id IS NOT NULL) * 100.0 / COUNT(*)
                FROM rezultate
            """)
            ratio = cur.fetchone()[0]
            print(f"📈 Overall mapping ratio: {ratio:.1f}%")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

def check_config():
    """Check configuration."""
    try:
        from backend.config import settings
        
        print("\n" + "=" * 70)
        print("CONFIGURATION CHECK")
        print("=" * 70 + "\n")
        
        llm_enabled = bool(getattr(settings, "llm_learn_from_upload_enabled", False))
        print(f"LLM Learning Enabled: {'✅ YES' if llm_enabled else '❌ NO'}")
        
        if not llm_enabled:
            print("\n⚠️  CRITICAL: LLM learning is DISABLED!")
            print("   FIX: Edit .env and set: LLM_LEARN_FROM_UPLOAD_ENABLED=true")
        
        # Check API
        from backend.llm_chat import audit_llm_has_credentials
        has_creds = audit_llm_has_credentials()
        print(f"LLM Credentials: {'✅ YES' if has_creds else '❌ NO'}")
        
        if not has_creds:
            print("\n⚠️  No LLM credentials found!")
            print("   FIX: Set ANTHROPIC_API_KEY in .env")
        
        print(f"\nMin score threshold: {getattr(settings, 'llm_learn_auto_apply_min_score', 86.0)}%")
        print(f"Max LLM calls per upload: {getattr(settings, 'llm_learn_max_calls_per_upload', 40)}")
        
    except Exception as e:
        print(f"❌ Config error: {e}")

def check_logs():
    """Check error logs for learning-related messages."""
    try:
        from pathlib import Path
        log_file = Path("upload_eroare.txt")
        
        print("\n" + "=" * 70)
        print("LOGS CHECK (last 20 lines)")
        print("=" * 70 + "\n")
        
        if log_file.exists():
            lines = log_file.read_text().split('\n')
            relevant = [l for l in lines if any(x in l.lower() for x in ['llm', 'learn', 'alias', 'error'])]
            if relevant:
                print("Relevant log lines:")
                for line in relevant[-20:]:
                    if line.strip():
                        print(f"  {line}")
            else:
                print("⚠️  No LLM-related logs found")
        else:
            print("⚠️  No log file found")
        
    except Exception as e:
        print(f"Error checking logs: {e}")

if __name__ == '__main__':
    check_config()
    check_database()
    check_logs()
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70 + "\n")
