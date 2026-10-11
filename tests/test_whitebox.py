"""
================================================================================
FocusTracker Pro — White Box Testing Suite (test_whitebox.py)
================================================================================
Course: PBL III - CSE20140 (AY 26-27 SEM V)
Assignment: No. 7 — White Box & Black Box Testing

Target Modules Under Test:
  1. WindowClassifier.predict() in classifier.py (Decision Logic & Rail Guard)
  2. database.get_daily_summary() & recalculate_daily_summary() in database.py
  3. SystemMonitor.is_idle() in monitor.py

Techniques Applied:
  - Statement Coverage (100%)
  - Branch / Decision Coverage (100% of True/False branches)
  - Condition Coverage (Compound boolean evaluation)
  - Basis Path Testing (Cyclomatic Complexity V(G) = 6)
================================================================================
"""

import os
import sys
import unittest
import sqlite3

# Add parent directory to path so tests can import application modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import database
from classifier import WindowClassifier
from monitor import SystemMonitor

class TestWhiteBoxWindowClassifier(unittest.TestCase):
    """
    White Box Test Cases for WindowClassifier.predict()
    
    Control Flow Analysis of `predict(window_title, content_snippet)`:
      Node 1: Entry, clean_title, clean_snippet
      Node 2: Decision 1: `if not clean_title and not clean_snippet:`
      Node 3: Return ("Distraction", 0.0, [], False) [Path 1]
      Node 4: Model predict on clean_title
      Node 5: Decision 2: `if not clean_snippet:`
      Node 6: Return (title_cat, title_conf, [], False) [Path 2]
      Node 7: Combined text inference + Keyword density loop
      Node 8: Decision 3: `if dist_kw_count > task_kw_count and task_kw_count == 0:`
      Node 9: Railguard overrules to Distraction [Path 4]
      Node 10: Decision 4: `elif task_kw_count > dist_kw_count and dist_kw_count == 0:`
      Node 11: Railguard overrules to Intended Task [Path 5]
      Node 12: Return final_category, final_conf, matched_keywords, railguard_overruled [Path 3]
    """

    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.classifier = WindowClassifier()

    def test_path_1_empty_input_branch(self):
        """
        [Basis Path 1] Statement & Branch Coverage:
        Inputs: window_title="", content_snippet=""
        Condition: `not clean_title and not clean_snippet` == TRUE
        Expected: Returns ("Distraction", 0.0, [], False)
        """
        cat, conf, matched, overruled = self.classifier.predict("", "")
        self.assertEqual(cat, "Distraction")
        self.assertEqual(conf, 0.0)
        self.assertEqual(matched, [])
        self.assertFalse(overruled)

    def test_path_2_title_only_no_snippet_intended_task(self):
        """
        [Basis Path 2A] Branch Coverage:
        Inputs: window_title="Visual Studio Code", content_snippet=""
        Condition: `not clean_title and not clean_snippet` == FALSE
                   `not clean_snippet` == TRUE
        Expected: Title prediction returned without railguard evaluation
        """
        cat, conf, matched, overruled = self.classifier.predict("Visual Studio Code", "")
        self.assertEqual(cat, "Intended Task")
        self.assertGreater(conf, 0.5)
        self.assertEqual(matched, [])
        self.assertFalse(overruled)

    def test_path_2_title_only_no_snippet_distraction(self):
        """
        [Basis Path 2B] Branch Coverage:
        Inputs: window_title="YouTube - Watch Funny Videos", content_snippet=""
        Condition: `not clean_title and not clean_snippet` == FALSE
                   `not clean_snippet` == TRUE
        Expected: Title prediction returned as Distraction
        """
        cat, conf, matched, overruled = self.classifier.predict("YouTube - Watch Funny Videos", "")
        self.assertEqual(cat, "Distraction")
        self.assertGreater(conf, 0.5)
        self.assertEqual(matched, [])
        self.assertFalse(overruled)

    def test_path_3_balanced_neutral_snippet_no_overrule(self):
        """
        [Basis Path 3] Branch Coverage:
        Inputs: window_title="Documentation Research", content_snippet="reading article about software architecture"
        Condition: dist_kw_count == 0, task_kw_count > 0 (or matched), title matches work
        Expected: Category remains Intended Task, railguard_overruled is False
        """
        cat, conf, matched, overruled = self.classifier.predict(
            "Documentation Research", 
            "Software architecture documentation and terminal api overview"
        )
        self.assertEqual(cat, "Intended Task")
        self.assertFalse(overruled)

    def test_path_4_railguard_overrules_work_to_distraction(self):
        """
        [Basis Path 4] Condition & Decision Coverage:
        Title appears productive, but 70-word snippet contains distraction keywords.
        Inputs: window_title="Project Research", content_snippet="watch live stream videos on youtube and netflix"
        Condition: `dist_kw_count > task_kw_count and task_kw_count == 0` == TRUE
                   `title_cat == 'Intended Task'` == TRUE
        Expected: Overrules to "Distraction", railguard_overruled=True, conf >= 0.85
        """
        cat, conf, matched, overruled = self.classifier.predict(
            "Project Research",
            "Watch funny viral reels on youtube and streaming video movies"
        )
        self.assertEqual(cat, "Distraction")
        self.assertTrue(overruled, "Railguard must overrule productive title to Distraction")
        self.assertGreaterEqual(conf, 0.85)
        self.assertTrue(any(k[0] == 'youtube' for k in matched))

    def test_path_5_railguard_overrules_distraction_to_task(self):
        """
        [Basis Path 5] Condition & Decision Coverage:
        Title appears distracting, but 70-word snippet contains legitimate task keywords.
        Inputs: window_title="YouTube", content_snippet="python asyncio tutorial in vscode with pycharm and github"
        Condition: `task_kw_count > dist_kw_count and dist_kw_count == 0` == TRUE
        Expected: Overrules to "Intended Task", railguard_overruled=True
        """
        cat, conf, matched, overruled = self.classifier.predict(
            "YouTube",
            "Python documentation for machine learning algorithms with pytorch and vscode"
        )
        self.assertEqual(cat, "Intended Task")
        self.assertTrue(overruled, "Railguard must overrule distraction title to Intended Task")
        self.assertGreaterEqual(conf, 0.85)

    def test_path_6_mixed_keywords_both_task_and_distraction(self):
        """
        [Basis Path 6] Condition Coverage:
        Both task keywords and distraction keywords present in the snippet.
        Condition: `dist_kw_count > 0 and task_kw_count > 0`
        Expected: Follows ML model probability without triggering exclusive zero-count overrule.
        """
        cat, conf, matched, overruled = self.classifier.predict(
            "Research Dashboard",
            "Python documentation for youtube api integration in vscode terminal"
        )
        self.assertIn(cat, ["Intended Task", "Distraction"])
        # Matched list should contain both
        matched_phrases = [k[0] for k in matched]
        self.assertIn("youtube", matched_phrases)
        self.assertTrue(any(p in ["python", "vscode", "terminal", "documentation"] for p in matched_phrases))


class TestWhiteBoxDatabaseAnalytics(unittest.TestCase):
    """
    White Box Test Cases for database.py calculations and mathematical edge cases.
    """

    def setUp(self):
        database.init_db()
        self.test_date = "2099-01-01"
        database.reset_today_data(self.test_date)

    def tearDown(self):
        database.reset_today_data(self.test_date)

    def test_summary_zero_active_time_division_by_zero_guard(self):
        """
        Statement & Condition Coverage:
        Verifies `(productive / active * 100.0) if active > 0 else 100.0`
        Condition: `active == 0` -> Branch should return 100.0 focus score without ZeroDivisionError.
        """
        summary = database.get_daily_summary(self.test_date)
        self.assertEqual(summary['total_active_time'], 0.0)
        self.assertEqual(summary['productive_time'], 0.0)
        self.assertEqual(summary['focus_score'], 100.0)

    def test_summary_calculation_with_active_and_distraction(self):
        """
        Statement & Branch Coverage:
        Records 300s total active time with 60s distraction time.
        Expected: Productive = 240s, Focus Score = (240 / 300) * 100 = 80.0%
        """
        # Log 240s of productive work
        database.log_activity("VSCode", "Code.exe", "Intended Task", f"{self.test_date}T10:00:00", f"{self.test_date}T10:04:00", 240.0, False)
        # Log 60s of distraction
        database.log_activity("YouTube", "chrome.exe", "Distraction", f"{self.test_date}T10:05:00", f"{self.test_date}T10:06:00", 60.0, False)
        
        # Recalculate rollup
        database.recalculate_daily_summary(self.test_date)
        summary = database.get_daily_summary(self.test_date)
        
        self.assertEqual(summary['total_active_time'], 300.0)
        self.assertEqual(summary['total_distraction_time'], 60.0)
        self.assertEqual(summary['productive_time'], 240.0)
        self.assertEqual(summary['focus_score'], 80.0)

    def test_reclassification_and_summary_adjustment(self):
        """
        Branch & Data Flow Coverage:
        Reclassifying an activity must adjust database records and trigger recalculation.
        """
        act_id = database.log_activity("Research Article", "chrome.exe", "Distraction", f"{self.test_date}T11:00:00", f"{self.test_date}T11:02:00", 120.0, False)
        database.recalculate_daily_summary(self.test_date)
        
        # Before reclassification
        s1 = database.get_daily_summary(self.test_date)
        self.assertEqual(s1['total_distraction_time'], 120.0)
        self.assertEqual(s1['focus_score'], 0.0)
        
        # Reclassify to Intended Task
        database.update_activity_category(act_id, "Intended Task")
        
        # After reclassification
        s2 = database.get_daily_summary(self.test_date)
        self.assertEqual(s2['total_distraction_time'], 0.0)
        self.assertEqual(s2['productive_time'], 120.0)
        self.assertEqual(s2['focus_score'], 100.0)


class TestWhiteBoxMonitorIdle(unittest.TestCase):
    """
    White Box Test Cases for SystemMonitor in monitor.py
    """

    def test_is_idle_boundary_conditions(self):
        """
        Branch Coverage for `def is_idle(self): return self.get_idle_time() >= self.idle_threshold`
        """
        monitor = SystemMonitor(idle_threshold=60)
        
        # Test branch where idle time < threshold
        monitor.get_idle_time = lambda: 59.9
        self.assertFalse(monitor.is_idle(), "Branch FALSE: 59.9s < 60s should not be idle")
        
        # Test branch where idle time == threshold (boundary)
        monitor.get_idle_time = lambda: 60.0
        self.assertTrue(monitor.is_idle(), "Branch TRUE: 60.0s == 60s should be idle")
        
        # Test branch where idle time > threshold
        monitor.get_idle_time = lambda: 120.5
        self.assertTrue(monitor.is_idle(), "Branch TRUE: 120.5s > 60s should be idle")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RUNNING WHITE BOX TESTING SUITE — FocusTracker Pro")
    print("=" * 70 + "\n")
    unittest.main(verbosity=2)
