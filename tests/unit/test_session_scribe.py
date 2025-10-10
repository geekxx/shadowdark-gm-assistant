#!/usr/bin/env python3

"""
Quick test script for the enhanced Session Scribe
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agents.session_scribe import summarize_text

# Sample Shadowdark transcript
SAMPLE_TRANSCRIPT = """
GM: You approach the crumbling tower. The stonework is ancient, covered in strange runes.
Kira: I want to examine the runes. Do I recognize them?
GM: Roll a WIS check.
Kira: *rolls* 15!
GM: These are draconic ward runes, likely protecting something inside. They're still active.
Thane: Can I find another way in? Maybe around back?
GM: *rolls* You find a narrow window about 20 feet up on the north side.
Kira: I'll cast Light on a stone and toss it through the window.
GM: The stone illuminates a dusty chamber. You see three skeletal figures turn toward the light.
Thane: Undead! I'm climbing up.
GM: STR check to climb the cracked stones.
Thane: *rolls* 12. Made it!
GM: The skeletons advance. Roll initiative.
*Combat ensues*
GM: After the fight, you find 30 gold pieces and a silver amulet with a moon symbol.
Kira: The amulet - does it radiate magic?
GM: Yes, faint divination magic. And you notice stairs leading down...
GM: That's where we'll end tonight. Kira, you get 1 XP for clever use of Light. Thane, 1 XP for brave climbing.
"""

if __name__ == "__main__":
    print("Testing Session Scribe...")
    print("=" * 50)
    
    try:
        # Test with mock LLM for now
        notes = summarize_text(SAMPLE_TRANSCRIPT, use_mock=True)
        print(notes)
        print("\n" + "=" * 50)
        print("✅ Session Scribe test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()