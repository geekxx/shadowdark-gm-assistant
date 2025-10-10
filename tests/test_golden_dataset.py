#!/usr/bin/env python3

"""
Test runner for Session Scribe quality evaluation

This script runs the Session Scribe agent against golden dataset transcripts
and evaluates the quality of generated notes using multiple metrics.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple
import difflib
from dataclasses import dataclass

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agents.session_scribe import summarize_text

@dataclass
class TestResult:
    transcript_file: str
    expected_file: str
    generated_notes: str
    similarity_score: float
    checklist_scores: Dict[str, bool]
    overall_score: float

class SessionScribeEvaluator:
    """Evaluates Session Scribe output quality against golden dataset"""
    
    def __init__(self, golden_dir: Path):
        self.golden_dir = golden_dir
        self.transcript_files = list(golden_dir.glob("transcript_*.md"))
        self.expected_files = list(golden_dir.glob("expected_*.md"))
    
    def run_all_tests(self, use_mock: bool = True) -> List[TestResult]:
        """Run evaluation against all golden dataset pairs"""
        results = []
        
        for transcript_file in self.transcript_files:
            # Find corresponding expected file
            base_name = transcript_file.name.replace("transcript_", "expected_")
            expected_file = self.golden_dir / base_name
            
            if not expected_file.exists():
                print(f"Warning: No expected file found for {transcript_file.name}")
                continue
            
            result = self.evaluate_single_transcript(transcript_file, expected_file, use_mock)
            results.append(result)
            
        return results
    
    def evaluate_single_transcript(self, transcript_file: Path, expected_file: Path, use_mock: bool) -> TestResult:
        """Evaluate a single transcript against its expected output"""
        
        # Read input and expected output
        with open(transcript_file, 'r') as f:
            transcript = f.read()
        
        with open(expected_file, 'r') as f:
            expected = f.read()
        
        # Generate notes using Session Scribe
        generated = summarize_text(transcript, use_mock=use_mock)
        
        # Calculate similarity score
        similarity = self.calculate_similarity(expected, generated)
        
        # Run quality checklist
        checklist_scores = self.run_quality_checklist(generated, expected)
        
        # Calculate overall score
        overall = self.calculate_overall_score(similarity, checklist_scores)
        
        return TestResult(
            transcript_file=transcript_file.name,
            expected_file=expected_file.name,
            generated_notes=generated,
            similarity_score=similarity,
            checklist_scores=checklist_scores,
            overall_score=overall
        )
    
    def calculate_similarity(self, expected: str, generated: str) -> float:
        """Calculate semantic similarity between expected and generated notes"""
        
        # Clean and normalize text for comparison
        expected_lines = [line.strip() for line in expected.split('\n') if line.strip()]
        generated_lines = [line.strip() for line in generated.split('\n') if line.strip()]
        
        # Use SequenceMatcher for similarity
        matcher = difflib.SequenceMatcher(None, expected_lines, generated_lines)
        return matcher.ratio()
    
    def run_quality_checklist(self, generated: str, expected: str) -> Dict[str, bool]:
        """Run quality checklist against generated notes"""
        
        checklist = {
            "has_date": generated.startswith('['),
            "has_summary": "Session Summary" in generated,
            "has_cast": "Cast of Characters" in generated,
            "has_locations": "Locations Visited" in generated,
            "has_scenes": "Scenes & Encounters" in generated,
            "has_treasure": "Treasure & XP Hooks" in generated,
            "has_rumors": "Rumors & Leads" in generated,
            "has_prep": "Prep For Next" in generated,
            "uses_shadowdark_style": self.check_shadowdark_style(generated),
            "appropriate_length": 200 < len(generated) < 2000,
            "mentions_key_npcs": self.check_npc_mentions(generated, expected),
            "includes_locations": self.check_location_mentions(generated, expected)
        }
        
        return checklist
    
    def check_shadowdark_style(self, text: str) -> bool:
        """Check if text follows Shadowdark style guidelines"""
        # Look for Shadowdark-style elements
        style_indicators = [
            "Close" in text or "Near" in text or "Far" in text,  # Distance zones
            "check vs DC" in text or "vs DC" in text,            # Ability checks
            "HD" in text or "AC" in text,                        # Stat block format
        ]
        return any(style_indicators)
    
    def check_npc_mentions(self, generated: str, expected: str) -> bool:
        """Check if key NPCs from expected output are mentioned in generated"""
        # Extract NPC names from expected (simplified approach)
        import re
        expected_npcs = re.findall(r'\b[A-Z][a-z]+\b(?:\s+\([^)]+\))?', expected)
        generated_lower = generated.lower()
        
        # Check if most NPCs are mentioned
        mentioned = sum(1 for npc in expected_npcs if npc.lower() in generated_lower)
        return mentioned >= len(expected_npcs) * 0.5  # At least 50% mentioned
    
    def check_location_mentions(self, generated: str, expected: str) -> bool:
        """Check if key locations are mentioned"""
        # Simple heuristic - look for capitalized location names
        import re
        expected_locations = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', expected)
        location_keywords = ['tower', 'tavern', 'forest', 'cave', 'pass', 'room']
        
        generated_lower = generated.lower()
        has_locations = any(keyword in generated_lower for keyword in location_keywords)
        return has_locations
    
    def calculate_overall_score(self, similarity: float, checklist: Dict[str, bool]) -> float:
        """Calculate overall quality score"""
        checklist_score = sum(checklist.values()) / len(checklist)
        
        # Weight similarity and checklist scores
        overall = (similarity * 0.4) + (checklist_score * 0.6)
        return overall
    
    def print_results(self, results: List[TestResult]):
        """Print detailed evaluation results"""
        print("\n" + "="*60)
        print("SESSION SCRIBE EVALUATION RESULTS")
        print("="*60)
        
        total_score = 0
        for result in results:
            print(f"\n📝 {result.transcript_file}")
            print(f"   Similarity Score: {result.similarity_score:.2f}")
            print(f"   Overall Score: {result.overall_score:.2f}")
            
            # Show failed checklist items
            failed_checks = [k for k, v in result.checklist_scores.items() if not v]
            if failed_checks:
                print(f"   ❌ Failed checks: {', '.join(failed_checks)}")
            else:
                print(f"   ✅ All quality checks passed!")
            
            total_score += result.overall_score
        
        avg_score = total_score / len(results) if results else 0
        print(f"\n🎯 OVERALL AVERAGE SCORE: {avg_score:.2f}")
        
        if avg_score >= 0.8:
            print("🎉 Excellent! Session Scribe is performing very well.")
        elif avg_score >= 0.6:
            print("👍 Good performance. Some areas for improvement.")
        else:
            print("⚠️  Performance needs improvement. Review failed checks.")
        
        print("="*60)

def main():
    """Run the evaluation"""
    golden_dir = Path(__file__).parent / "golden"
    
    if not golden_dir.exists():
        print(f"❌ Golden dataset directory not found: {golden_dir}")
        return
    
    evaluator = SessionScribeEvaluator(golden_dir)
    print(f"🔍 Found {len(evaluator.transcript_files)} test transcripts")
    
    # Run evaluation
    results = evaluator.run_all_tests(use_mock=True)
    
    # Print results
    evaluator.print_results(results)

if __name__ == "__main__":
    main()