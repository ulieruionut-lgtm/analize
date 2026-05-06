#!/usr/bin/env python3
"""
Real-time terminal monitor for LLM learning.
Shows live updates in the terminal as learning happens.

Usage:
    python learning_monitor_live.py
"""
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from collections import deque

sys.path.insert(0, str(Path(__file__).parent))

# Terminal colors and formatting
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def clear_screen():
    """Clear terminal screen."""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


class TerminalLearningMonitor:
    """Real-time learning monitor for terminal."""
    
    def __init__(self):
        self.events = deque(maxlen=20)  # Last 20 events
        self.stats = {
            'total_events': 0,
            'aliases_learned': 0,
            'errors': 0,
            'llm_calls': 0,
            'success_rate': 0,
        }
        self.running = True
        self.last_update = datetime.now()
    
    def subscribe_to_events(self):
        """Subscribe to the learning event bus."""
        try:
            from backend.learning_events import get_event_bus
            
            bus = get_event_bus()
            self.bus = bus
            
            # Subscribe to events
            bus.subscribe(self.on_event)
            print(f"{Colors.OKGREEN}✓ Subscribed to learning events{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}✗ Failed to subscribe: {e}{Colors.ENDC}")
            return False
        return True
    
    def on_event(self, event):
        """Handle new learning event."""
        self.events.appendleft({
            'type': event.event_type,
            'name': event.analysis_name,
            'mapped': event.mapped_to,
            'score': event.score,
            'time': event.timestamp,
            'error': event.error,
        })
        self.update_stats()
    
    def update_stats(self):
        """Update statistics from event bus."""
        try:
            if hasattr(self, 'bus'):
                stats = self.bus.get_statistics()
                self.stats = stats
                self.last_update = datetime.now()
        except Exception as e:
            pass
    
    def format_event(self, event) -> str:
        """Format event for display."""
        icon = '📝'
        color = Colors.ENDC
        
        if event['type'] == 'alias_learned':
            icon = '✅'
            color = Colors.OKGREEN
            return (
                f"{color}{icon} {event['name']:<20} "
                f"→ {event['mapped']:<25} "
                f"{Colors.BOLD}{event['score']:.1f}%{Colors.ENDC} "
                f"{Colors.OKCYAN}{event['time'].strftime('%H:%M:%S')}{Colors.ENDC}"
            )
        elif event['type'] == 'error':
            icon = '❌'
            color = Colors.FAIL
            return (
                f"{color}{icon} {event['name']:<20} "
                f"Error: {event['error'][:40]:<40}{Colors.ENDC} "
                f"{Colors.OKCYAN}{event['time'].strftime('%H:%M:%S')}{Colors.ENDC}"
            )
        elif event['type'] == 'llm_call':
            icon = '🔍'
            color = Colors.OKBLUE
            return (
                f"{color}{icon} Analyzing {event['name']:<30}{Colors.ENDC} "
                f"{Colors.OKCYAN}{event['time'].strftime('%H:%M:%S')}{Colors.ENDC}"
            )
        else:
            return f"{icon} {event['name']}"
    
    def render(self):
        """Render the monitor display."""
        clear_screen()
        
        print(f"\n{Colors.HEADER}{Colors.BOLD}")
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "🧠 LLM LEARNING MONITOR (REAL-TIME)" + " " * 23 + "║")
        print("╚" + "═" * 78 + "╝")
        print(f"{Colors.ENDC}\n")
        
        # Statistics row
        print(f"{Colors.BOLD}📊 STATISTICS:{Colors.ENDC}")
        print(f"  Total Events: {Colors.OKBLUE}{self.stats.get('total_events', 0):,}{Colors.ENDC} | "
              f"Aliases Learned: {Colors.OKGREEN}{self.stats.get('aliases_learned', 0):,}{Colors.ENDC} | "
              f"LLM Calls: {Colors.OKCYAN}{self.stats.get('llm_calls', 0):,}{Colors.ENDC} | "
              f"Errors: {Colors.FAIL}{self.stats.get('errors', 0):,}{Colors.ENDC}")
        
        success_rate = self.stats.get('success_rate', 0)
        bar_length = 20
        filled = int(bar_length * success_rate / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        print(f"\n  Success Rate: {Colors.BOLD}{success_rate:.1f}%{Colors.ENDC}")
        print(f"  [{bar}]")
        
        print(f"\n{Colors.BOLD}📝 RECENT EVENTS:{Colors.ENDC}")
        print("  " + "─" * 76)
        
        if not self.events:
            print(f"  {Colors.WARNING}⏳ Waiting for learning events...{Colors.ENDC}")
            print(f"  {Colors.OKCYAN}Upload a PDF with unknown analyses to see events{Colors.ENDC}")
        else:
            for event in self.events:
                print(f"  {self.format_event(event)}")
        
        print("  " + "─" * 76)
        
        # Footer
        print(f"\n{Colors.OKCYAN}Last update: {self.last_update.strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"{Colors.WARNING}Refreshing every 1 second... (Press Ctrl+C to exit){Colors.ENDC}\n")
    
    def run(self):
        """Run the monitor loop."""
        if not self.subscribe_to_events():
            return
        
        print(f"{Colors.OKGREEN}Monitor started. Waiting for events...{Colors.ENDC}\n")
        time.sleep(2)
        
        try:
            while self.running:
                self.render()
                time.sleep(1)
        except KeyboardInterrupt:
            clear_screen()
            print(f"\n{Colors.OKGREEN}✓ Monitor stopped.{Colors.ENDC}\n")
            sys.exit(0)


def main():
    """Main entry point."""
    try:
        monitor = TerminalLearningMonitor()
        monitor.run()
    except Exception as e:
        print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
