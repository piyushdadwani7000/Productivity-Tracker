"""
================================================================================
FocusTracker Pro — Machine Learning Classification Engine (classifier.py)
================================================================================
Role:
  Classifies window activities and web content into either:
    - "Intended Task" (Productive work: coding, docs, terminals, research)
    - "Distraction"   (Entertainment: social media, streaming, gaming)
    
  Uses a Scikit-Learn Machine Learning pipeline consisting of:
    1. TF-IDF Vectorizer (ngram_range=(1,2), sublinear_tf=True)
    2. Multinomial Naive Bayes (MultinomialNB) classifier
    3. Multi-Tiered Rail Guard Heuristic Analyzer for title overruling.

Linkages:
  - Interacts with `database.py` via `database.get_keywords()` to fetch training data.
  - Instantiated by `TrackingEngine` in `tracker.py` as `self.classifier`.
  - Retrained on-the-fly whenever a user edits keywords or reclassifies an activity in UI.
================================================================================
"""

import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import database

# -----------------------------------------------------------------------------
# WindowClassifier Class
# -----------------------------------------------------------------------------
class WindowClassifier:
    """
    NLP & Heuristic Classifier for desktop windows and web page snippets.
    Combines probabilistic Naive Bayes classification with explicit keyword guards.
    """

    def __init__(self):
        """
        Initializes the classifier instance and executes initial training against SQLite keywords.
        """
        self.model = None
        self.keywords_list = []
        self.train_model()

    # -------------------------------------------------------------------------
    # Model Training & Pipeline Assembly
    # -------------------------------------------------------------------------
    def train_model(self):
        """
        Fetches the latest keywords dictionary from the SQLite database
        and rebuilds/retrains the Scikit-Learn TF-IDF + MultinomialNB pipeline.
        
        Features:
          - n-gram range (1, 2): Captures both unigrams ('code') and bigrams ('vs code').
          - sublinear_tf=True: Uses sublinear scaling (1 + log(tf)) to prevent
            repetitive words from disproportionately skewing document frequency.
        """
        keywords = database.get_keywords()
        
        # Fallback dataset if database table is completely empty
        if not keywords:
            keywords = [('code', 'Intended Task'), ('video', 'Distraction')]
            
        self.keywords_list = keywords
        df_keywords = pd.DataFrame(keywords, columns=['phrase', 'category'])
        
        # Construct and fit scikit-learn text pipeline
        self.model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), 
            MultinomialNB()
        )
        self.model.fit(df_keywords['phrase'].str.lower(), df_keywords['category'])

    # -------------------------------------------------------------------------
    # Multi-Stage Prediction & Rail Guard Evaluation
    # -------------------------------------------------------------------------
    def predict(self, window_title: str, content_snippet: str = ""):
        """
        Predicts category based on window title and optional 70-word web content snippet.
        
        Execution Stages:
          1. Stage 1 (Title Baseline): Fast initial prediction solely on window title.
          2. Stage 2 (Snippet Analysis): Pipeline inference on combined (title + 70 words).
          3. Stage 3 (Keyword Density Scan): Exact word-boundary regex scan across keywords.
          4. Stage 4 (Rail Guard Overrule): If title indicates work, but body contains 
             unambiguous distraction keywords (or vice-versa), overrules preliminary label.
             
        Returns:
            Tuple of:
              - category (str): "Intended Task" or "Distraction"
              - confidence_score (float): Probability confidence (0.0 to 1.0)
              - matched_keywords (list): List of (phrase, category) tuples matched in text
              - railguard_overruled (bool): True if 70-word body content overrode window title
        """
        clean_title = (window_title or "").strip().lower()
        clean_snippet = (content_snippet or "").strip().lower()
        
        # Edge case: Empty input defaults to Distraction
        if not clean_title and not clean_snippet:
            return "Distraction", 0.0, [], False

        # --- Stage 1: Window Title Prediction ---
        title_cat = "Intended Task"
        title_conf = 0.5
        if self.model and clean_title:
            try:
                title_cat = self.model.predict([clean_title])[0]
                proba = self.model.predict_proba([clean_title])[0]
                title_conf = float(max(proba))
            except Exception:
                pass

        # Fast exit if no 70-word web snippet is available
        if not clean_snippet:
            return title_cat, title_conf, [], False

        # --- Stage 2: Combined Text Inference (Title + 70-word snippet) ---
        combined_text = f"{clean_title} {clean_snippet}"
        
        snippet_cat = title_cat
        snippet_conf = title_conf
        if self.model:
            try:
                snippet_cat = self.model.predict([combined_text])[0]
                proba = self.model.predict_proba([combined_text])[0]
                snippet_conf = float(max(proba))
            except Exception:
                pass

        # --- Stage 3: Exact Word-Boundary Keyword Density Scan ---
        matched_keywords = []
        task_kw_count = 0
        dist_kw_count = 0

        for phrase, cat in self.keywords_list:
            p = phrase.lower().strip()
            if not p:
                continue
            # Regex with word boundaries \b to avoid substring false positives (e.g. 'ass' in 'class')
            # 1. UI Display: Check combined text so UI badge shows all matched keywords
            if re.search(r'\b' + re.escape(p) + r'\b', combined_text):
                matched_keywords.append((p, cat))
                
            # 2. Rail Guard Overrule: Check snippet specifically to verify actual page body
            if re.search(r'\b' + re.escape(p) + r'\b', clean_snippet):
                if cat == "Intended Task":
                    task_kw_count += 1
                elif cat == "Distraction":
                    dist_kw_count += 1

        # --- Stage 4: Rail Guard Overruling Evaluation ---
        railguard_overruled = False
        final_category = snippet_cat
        final_conf = snippet_conf

        # Scenario A: Distraction content detected on an apparent work window
        if dist_kw_count > task_kw_count and task_kw_count == 0:
            if title_cat == "Intended Task":
                railguard_overruled = True
            final_category = "Distraction"
            final_conf = max(snippet_conf, 0.85)

        # Scenario B: Legitimate work content detected on an ambiguous title
        elif task_kw_count > dist_kw_count and dist_kw_count == 0:
            if title_cat == "Distraction":
                railguard_overruled = True
            final_category = "Intended Task"
            final_conf = max(snippet_conf, 0.85)

        return final_category, float(final_conf), matched_keywords, railguard_overruled

# -----------------------------------------------------------------------------
# Diagnostic CLI Verification
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    classifier = WindowClassifier()
    print("Testing 'Visual Studio Code':", classifier.predict("Visual Studio Code"))
    print("Testing 'Work Research' with YouTube snippet:", classifier.predict("Work Research", "Watch live gaming videos and funny cat reels on youtube streaming platform"))
    print("Testing 'Google Chrome' with Python snippet:", classifier.predict("Google Chrome", "Python standard library documentation for asyncio and multiprocessing algorithms"))

