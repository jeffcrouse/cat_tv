#!/usr/bin/env python3
"""Test if schedule time checking is working correctly."""

import sys
import os
from datetime import datetime, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from cat_tv.models import get_session, Schedule
    
    print("🕐 Schedule Time Check")
    print("=" * 40)
    
    now = datetime.now()
    current_time = now.time()
    current_day = now.weekday()  # 0=Monday, 6=Sunday
    
    print(f"Current time: {current_time.strftime('%I:%M %p')}")
    print(f"Current day: {current_day} (0=Mon, 6=Sun)")
    print()
    
    with get_session() as session:
        schedules = session.query(Schedule).filter_by(is_active=True).all()
        
        print(f"Found {len(schedules)} active schedules:")
        print()
        
        for sched in schedules:
            print(f"Schedule: {sched.name}")
            print(f"  Time: {sched.start_time.strftime('%I:%M %p')} - {sched.end_time.strftime('%I:%M %p')}")
            print(f"  Days: {sched.days_of_week}")
            
            # Check if active today
            active_days = [int(d) for d in sched.days_of_week.split(",")]
            is_today = current_day in active_days
            print(f"  Active today: {is_today}")
            
            # Check if in time window
            if is_today:
                if sched.start_time <= sched.end_time:
                    # Normal schedule
                    in_window = sched.start_time <= current_time < sched.end_time
                    print(f"  In time window: {in_window}")
                    if in_window:
                        print(f"  ✅ CURRENTLY ACTIVE!")
                    else:
                        print(f"  ⭕ Scheduled but not active now")
                else:
                    # Crosses midnight
                    in_window = current_time >= sched.start_time or current_time < sched.end_time
                    print(f"  In time window (crosses midnight): {in_window}")
                    if in_window:
                        print(f"  ✅ CURRENTLY ACTIVE!")
                    else:
                        print(f"  ⭕ Scheduled but not active now")
            else:
                print(f"  ⭕ Not active today")
            
            print()

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()