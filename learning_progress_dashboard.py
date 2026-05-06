#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Learning Progress Dashboard
===================================

Monitorizează progresul sistemului de învățare LLM.
Arată statistici despre alias-uri salvate, mapări, și acuratețe.

Utilizare:
  python learning_progress_dashboard.py
  python learning_progress_dashboard.py --export csv
  python learning_progress_dashboard.py --watch  # Live monitoring
"""
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

def print_header(title: str):
    print(f"\n{'='*80}")
    print(f"  {title:^76}")
    print(f"{'='*80}\n")

def print_section(title: str):
    print(f"\n📊 {title}")
    print("─" * 80)

def get_learning_stats() -> Dict[str, any]:
    """Colectează toate statisticile de learning."""
    try:
        from backend.database import get_cursor
        from backend.config import settings
        import psycopg2
        from datetime import datetime, timedelta
        
        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'llm_enabled': bool(getattr(settings, 'llm_learn_from_upload_enabled', False)),
            'total_uploads': 0,
            'total_aliases': 0,
            'aliases_this_week': 0,
            'aliases_this_month': 0,
            'unknown_pending': 0,
            'approved_aliases': 0,
            'mapping_ratio_overall': 0.0,
            'mapping_ratio_recent': 0.0,
            'top_laboratories': [],
            'top_learned_aliases': [],
            'daily_progress': [],
        }
        
        # 1. Total uploads
        try:
            with get_cursor(commit=False) as cur:
                cur.execute("SELECT COUNT(*) FROM buletin")
                stats['total_uploads'] = cur.fetchone()[0] if cur.fetchone() else 0
        except:
            pass
        
        # 2. Alias statistics
        try:
            with get_cursor(commit=False) as cur:
                # Total aliases
                cur.execute("SELECT COUNT(*) FROM alias_analiza")
                stats['total_aliases'] = cur.fetchone()[0] if cur.fetchone() else 0
                
                # Aliases this week
                cur.execute("""
                SELECT COUNT(*) FROM alias_analiza 
                WHERE created_at > NOW() - INTERVAL '7 days'
                """)
                stats['aliases_this_week'] = cur.fetchone()[0] if cur.fetchone() else 0
                
                # Aliases this month
                cur.execute("""
                SELECT COUNT(*) FROM alias_analiza 
                WHERE created_at > NOW() - INTERVAL '30 days'
                """)
                stats['aliases_this_month'] = cur.fetchone()[0] if cur.fetchone() else 0
                
                # Unknown pending review
                cur.execute("""
                SELECT COUNT(*) FROM analiza_necunoscuta 
                WHERE approved = FALSE
                """)
                stats['unknown_pending'] = cur.fetchone()[0] if cur.fetchone() else 0
                
                # Approved aliases
                cur.execute("""
                SELECT COUNT(*) FROM analiza_necunoscuta 
                WHERE approved = TRUE
                """)
                stats['approved_aliases'] = cur.fetchone()[0] if cur.fetchone() else 0
        except:
            pass
        
        # 3. Mapping ratio overall
        try:
            with get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT 
                  COUNT(*) FILTER (WHERE analiza_standard_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) as ratio
                FROM rezultate
                """)
                row = cur.fetchone()
                if row and row[0]:
                    stats['mapping_ratio_overall'] = round(float(row[0]), 1)
        except:
            pass
        
        # 4. Mapping ratio recent (last 7 days)
        try:
            with get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT 
                  COUNT(*) FILTER (WHERE analiza_standard_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) as ratio
                FROM rezultate
                WHERE created_at > NOW() - INTERVAL '7 days'
                """)
                row = cur.fetchone()
                if row and row[0]:
                    stats['mapping_ratio_recent'] = round(float(row[0]), 1)
        except:
            pass
        
        # 5. Top laboratories
        try:
            with get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT 
                  COALESCE(l.nume, 'Unknown') as lab_name,
                  COUNT(DISTINCT a.pattern) as aliases_learned,
                  COUNT(DISTINCT a.id) as total_aliases
                FROM alias_analiza a
                LEFT JOIN laborator l ON a.laborator_id = l.id
                GROUP BY l.id, l.nume
                ORDER BY aliases_learned DESC
                LIMIT 5
                """)
                stats['top_laboratories'] = [
                    {'name': row[0], 'learned': row[1], 'total': row[2]}
                    for row in cur.fetchall() or []
                ]
        except:
            pass
        
        # 6. Top learned aliases
        try:
            with get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT 
                  pattern,
                  scor_match,
                  created_at
                FROM alias_analiza
                ORDER BY created_at DESC
                LIMIT 10
                """)
                stats['top_learned_aliases'] = [
                    {'pattern': row[0], 'score': row[1], 'date': row[2].isoformat() if row[2] else None}
                    for row in cur.fetchall() or []
                ]
        except:
            pass
        
        # 7. Daily progress (last 7 days)
        try:
            with get_cursor(commit=False) as cur:
                cur.execute("""
                SELECT 
                  DATE(created_at) as date,
                  COUNT(*) as count
                FROM alias_analiza
                WHERE created_at > NOW() - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date ASC
                """)
                stats['daily_progress'] = [
                    {'date': row[0].isoformat(), 'aliases': row[1]}
                    for row in cur.fetchall() or []
                ]
        except:
            pass
        
        return stats
    
    except Exception as e:
        return {'error': str(e)[:200]}

def print_dashboard(stats: Dict) -> None:
    """Tipărește dashboard în format uman-readable."""
    print_header("🤖 LEARNING PROGRESS DASHBOARD")
    
    if 'error' in stats:
        print(f"❌ Error: {stats['error']}\n")
        return
    
    # Status
    print_section("System Status")
    llm_status = "✅ ENABLED" if stats['llm_enabled'] else "❌ DISABLED"
    print(f"LLM Learning: {llm_status}")
    print(f"Last Update: {stats['timestamp']}")
    
    # Global stats
    print_section("Global Statistics")
    print(f"Total Uploads: {stats['total_uploads']:,}")
    print(f"Total Aliases Learned: {stats['total_aliases']:,}")
    print(f"Pending Review: {stats['unknown_pending']:,}")
    print(f"Approved Aliases: {stats['approved_aliases']:,}")
    print(f"Overall Mapping Ratio: {stats['mapping_ratio_overall']:.1f}%")
    print(f"Recent Mapping Ratio (7d): {stats['mapping_ratio_recent']:.1f}%")
    
    # Weekly/Monthly progress
    print_section("Learning Progress")
    print(f"Aliases Learned (This Week): {stats['aliases_this_week']:,}")
    print(f"Aliases Learned (This Month): {stats['aliases_this_month']:,}")
    weekly_avg = stats['aliases_this_week'] / 7 if stats['aliases_this_week'] > 0 else 0
    print(f"Daily Average (This Week): {weekly_avg:.1f}")
    
    # Top laboratories
    if stats['top_laboratories']:
        print_section("Top Laboratories by Learning")
        for i, lab in enumerate(stats['top_laboratories'], 1):
            print(f"{i}. {lab['name']}")
            print(f"   Aliases Learned: {lab['learned']}, Total: {lab['total']}")
    
    # Daily progress chart
    if stats['daily_progress']:
        print_section("Daily Progress (Last 7 Days)")
        max_count = max(d['aliases'] for d in stats['daily_progress']) or 1
        for day_stat in stats['daily_progress']:
            date_str = day_stat['date']
            count = day_stat['aliases']
            bar_len = int(40 * count / max_count)
            bar = '█' * bar_len
            print(f"{date_str}: {bar} {count}")
    
    # Recent aliases
    if stats['top_learned_aliases']:
        print_section("Recently Learned Aliases")
        for i, alias in enumerate(stats['top_learned_aliases'][:5], 1):
            date_str = alias['date'][:10] if alias['date'] else "?"
            print(f"{i}. {alias['pattern']:<20} (Score: {alias['score']:.0f}%, Date: {date_str})")
    
    print("\n" + "="*80 + "\n")

def export_csv(stats: Dict, filename: str = "learning_progress.csv") -> None:
    """Exportă statistici în CSV."""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value', 'Timestamp'])
        writer.writerow(['LLM Enabled', stats['llm_enabled'], stats['timestamp']])
        writer.writerow(['Total Uploads', stats['total_uploads'], stats['timestamp']])
        writer.writerow(['Total Aliases', stats['total_aliases'], stats['timestamp']])
        writer.writerow(['This Week', stats['aliases_this_week'], stats['timestamp']])
        writer.writerow(['This Month', stats['aliases_this_month'], stats['timestamp']])
        writer.writerow(['Pending Review', stats['unknown_pending'], stats['timestamp']])
        writer.writerow(['Mapping Ratio %', stats['mapping_ratio_overall'], stats['timestamp']])
    
    print(f"✅ Exported to {filename}")

def watch_progress(interval: int = 60) -> None:
    """Monitorizează progresul în timp real."""
    print(f"🔍 Monitoring progress (updating every {interval} seconds)...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            stats = get_learning_stats()
            print("\033[2J\033[H")  # Clear screen
            print_dashboard(stats)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n✋ Monitoring stopped")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Learning Progress Dashboard')
    parser.add_argument('--export', nargs='?', const='csv', choices=['csv', 'json'],
                      help='Export results to file')
    parser.add_argument('--watch', action='store_true', help='Live monitoring mode')
    parser.add_argument('--interval', type=int, default=60,
                      help='Update interval in seconds (for --watch)')
    
    args = parser.parse_args()
    
    stats = get_learning_stats()
    
    if args.watch:
        watch_progress(args.interval)
    else:
        print_dashboard(stats)
        
        if args.export == 'csv':
            export_csv(stats)
        elif args.export == 'json':
            print(json.dumps(stats, indent=2))
