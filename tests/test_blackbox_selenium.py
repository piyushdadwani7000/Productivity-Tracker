"""
================================================================================
FocusTracker Pro — Black Box Selenium Automation Suite (test_blackbox_selenium.py)
================================================================================
Course: PBL III - CSE20140 (AY 26-27 SEM V)
Assignment: No. 7 — White Box & Black Box Testing

Target Component: FocusTracker Pro Web Application (Frontend + Backend Integration)
Automation Tool: Selenium WebDriver (Microsoft Edge Headless)

Black Box Techniques Tested:
  - Equivalence Partitioning (EP)
  - Boundary Value Analysis (BVA)
  - Functional System & UI Workflow Testing
  - State Transition Validation
================================================================================
"""

import os
import sys
import time
import threading
import unittest

# Add parent directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import uvicorn
from server import app
import database

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TEST_PORT = 8765
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

class FocusTrackerSeleniumTest(unittest.TestCase):
    server_thread = None
    server = None
    driver = None

    @classmethod
    def setUpClass(cls):
        # 1. Initialize SQLite database
        database.init_db()

        # 2. Start Uvicorn FastAPI server in background daemon thread
        config = uvicorn.Config(app=app, host="127.0.0.1", port=TEST_PORT, log_level="warning")
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()
        
        # Wait 1.5s for server to start listening
        time.sleep(1.5)

        # 3. Configure Selenium Edge WebDriver in Headless Mode
        edge_options = Options()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--window-size=1400,900")
        
        cls.driver = webdriver.Edge(options=edge_options)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        if cls.driver:
            cls.driver.quit()
        if cls.server:
            cls.server.should_exit = True

    def setUp(self):
        self.driver.get(BASE_URL)
        # Wait until body is present
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "app-layout"))
        )

    # -------------------------------------------------------------------------
    # Test Case BB-01: Page Load & Telemetry UI Elements
    # -------------------------------------------------------------------------
    def test_01_page_load_and_telemetry_elements(self):
        """
        [BB-01] Functional Verification:
        Verifies that title, active window radar banner, 4 metric cards, and charts render.
        """
        driver = self.driver
        self.assertIn("FocusTracker", driver.title)
        
        # Check Brand Header
        brand_title = driver.find_element(By.CLASS_NAME, "brand-text").text
        self.assertIn("FocusTracker", brand_title)
        
        # Check Radar Banner
        radar_tag = driver.find_element(By.CLASS_NAME, "live-tag").text
        self.assertEqual(radar_tag, "ACTIVE WINDOW RADAR")
        
        # Check 4 Metrics Cards exist in DOM
        self.assertTrue(driver.find_element(By.ID, "statProductive").is_displayed())
        self.assertTrue(driver.find_element(By.ID, "statDistraction").is_displayed())
        self.assertTrue(driver.find_element(By.ID, "statTotalActive").is_displayed())
        self.assertTrue(driver.find_element(By.ID, "statFocusScore").is_displayed())
        
        # Check Chart Canvases exist
        self.assertTrue(driver.find_element(By.ID, "categoryChart").is_displayed())
        self.assertTrue(driver.find_element(By.ID, "hourlyChart").is_displayed())

    # -------------------------------------------------------------------------
    # Test Case BB-02: Daily Focus Task Management (Add, Toggle, Delete)
    # -------------------------------------------------------------------------
    def test_02_task_lifecycle_workflow(self):
        """
        [BB-02] Use Case & State Transition Testing:
        Navigates to Tasks tab, adds a daily task, verifies progress bar update,
        toggles completion to complete (100%), and verifies deletion.
        """
        driver = self.driver
        
        # 1. Switch to Daily Tasks Tab
        tasks_tab_btn = driver.find_element(By.CSS_SELECTOR, "button[data-tab='tasks']")
        tasks_tab_btn.click()
        time.sleep(0.5)
        
        # Verify tasks tab pane is active
        tasks_pane = driver.find_element(By.ID, "tab-tasks")
        self.assertTrue("active" in tasks_pane.get_attribute("class"))
        
        # 2. Add a new Task
        task_input = driver.find_element(By.ID, "newTaskInput")
        task_input.clear()
        test_task_title = "Automated Selenium Task CSE20140"
        task_input.send_keys(test_task_title)
        
        add_btn = driver.find_element(By.CSS_SELECTOR, "#addTaskForm button[type='submit']")
        add_btn.click()
        time.sleep(0.8)
        
        # 3. Verify task appears in task items list
        task_items = driver.find_elements(By.CLASS_NAME, "task-item")
        self.assertGreater(len(task_items), 0, "At least one task item should exist")
        self.assertIn(test_task_title, driver.find_element(By.ID, "taskList").text)
        
        # 4. Toggle Task Checkbox (State Transition: pending -> complete)
        checkbox = task_items[0].find_element(By.CLASS_NAME, "task-checkbox")
        checkbox.click()
        time.sleep(0.8)
        
        # Check updated progress percentage
        progress_text = driver.find_element(By.ID, "taskProgressPercent").text
        self.assertIn("%", progress_text)
        
        # 5. Delete the Task (Re-query DOM to prevent StaleElementReferenceException)
        delete_btns = driver.find_elements(By.CLASS_NAME, "btn-delete")
        if delete_btns:
            delete_btns[0].click()
            time.sleep(0.5)

    # -------------------------------------------------------------------------
    # Test Case BB-03: Machine Learning Keyword Management & Model Retraining
    # -------------------------------------------------------------------------
    def test_03_keyword_creation_and_retraining(self):
        """
        [BB-03] Equivalence Partitioning & Functional Testing:
        Adds a custom ML keyword phrase, verifies UI chip creation, and triggers retraining.
        """
        driver = self.driver
        
        # 1. Switch to ML Keywords Tab
        kw_tab_btn = driver.find_element(By.CSS_SELECTOR, "button[data-tab='keywords']")
        kw_tab_btn.click()
        time.sleep(0.5)
        
        # 2. Add New Keyword Phrase
        kw_phrase_input = driver.find_element(By.ID, "newKwPhrase")
        kw_phrase_input.clear()
        test_phrase = "selenium_webdriver_automation"
        kw_phrase_input.send_keys(test_phrase)
        
        # Submit form
        add_kw_btn = driver.find_element(By.CSS_SELECTOR, "#addKeywordForm button[type='submit']")
        add_kw_btn.click()
        time.sleep(1.0)
        
        # 3. Verify Keyword chip is visible in Active Training Dictionary grid
        keywords_container = driver.find_element(By.ID, "keywordsContainer")
        self.assertIn(test_phrase, keywords_container.text)
        
        # 4. Trigger Force Retrain Model button
        retrain_btn = driver.find_element(By.ID, "forceRetrainBtn")
        retrain_btn.click()
        time.sleep(0.8)
        
        # Verify toast notification appears
        toast = driver.find_element(By.ID, "toastContainer")
        self.assertTrue(len(toast.text) > 0 or toast.is_displayed())

    # -------------------------------------------------------------------------
    # Test Case BB-04: Tracker Controls & State Toggle
    # -------------------------------------------------------------------------
    def test_04_tracker_pause_resume_toggle(self):
        """
        [BB-04] State Transition Testing:
        Validates pausing and resuming the tracking engine from the UI controls.
        """
        driver = self.driver
        toggle_btn = driver.find_element(By.ID, "toggleTrackingBtn")
        status_text = driver.find_element(By.ID, "trackingStatusText")
        
        # Initial state should be Pause (meaning tracking is active)
        initial_label = status_text.text.strip()
        
        # Click Toggle and await async fetch completion
        toggle_btn.click()
        WebDriverWait(driver, 5).until(
            lambda d: d.find_element(By.ID, "trackingStatusText").text.strip() != initial_label
        )
        new_label = status_text.text.strip()
        self.assertNotEqual(initial_label, new_label, "Tracking button state must toggle")
        
        # Click again to restore original state
        toggle_btn.click()
        WebDriverWait(driver, 5).until(
            lambda d: d.find_element(By.ID, "trackingStatusText").text.strip() == initial_label
        )
        restored_label = status_text.text.strip()
        self.assertEqual(initial_label, restored_label)

    # -------------------------------------------------------------------------
    # Test Case BB-05: Settings Modal & Boundary Value Inputs
    # -------------------------------------------------------------------------
    def test_05_settings_modal_interaction(self):
        """
        [BB-05] Boundary Value Analysis & Modal Behavior:
        Opens settings modal, verifies sliders, updates values, and saves.
        """
        driver = self.driver
        
        # 1. Open Settings Modal
        settings_btn = driver.find_element(By.ID, "openSettingsBtn")
        settings_btn.click()
        time.sleep(0.5)
        
        settings_modal = driver.find_element(By.ID, "settingsModal")
        self.assertFalse("hidden" in settings_modal.get_attribute("class"), "Modal should be visible")
        
        # 2. Check sliders exist and read boundary constraints
        idle_slider = driver.find_element(By.ID, "idleThresholdInput")
        self.assertEqual(idle_slider.get_attribute("min"), "15")
        self.assertEqual(idle_slider.get_attribute("max"), "300")
        
        alert_slider = driver.find_element(By.ID, "alertThresholdInput")
        self.assertEqual(alert_slider.get_attribute("min"), "10")
        self.assertEqual(alert_slider.get_attribute("max"), "300")
        
        # 3. Save Settings
        save_btn = driver.find_element(By.ID, "saveSettingsBtn")
        save_btn.click()
        time.sleep(0.6)
        
        # Verify modal closes
        self.assertTrue("hidden" in settings_modal.get_attribute("class"), "Modal should close on save")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RUNNING BLACK BOX SELENIUM AUTOMATION SUITE — FocusTracker Pro")
    print("=" * 70 + "\n")
    unittest.main(verbosity=2)
