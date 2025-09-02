#!/usr/bin/env python3
"""Simple display test - just run this to see what fails."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from cat_tv.display import DisplayController
    print("✅ Display import OK")
    
    controller = DisplayController()
    print("✅ Controller created OK")
    
    print("Testing turn_off()...")
    result = controller.turn_off()
    print(f"turn_off result: {result}")
    
    print("Testing turn_on()...")  
    result = controller.turn_on()
    print(f"turn_on result: {result}")
    
    print("✅ All tests passed")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()