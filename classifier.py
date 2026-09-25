import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import database

class WindowClassifier:
    def __init__(self):
        self.model = None
        self.keywords_list = []
        self.train_model()

    def train_model(self):
        """Fetches keywords and feedback from the database and retrains the model."""
        keywords = database.get_keywords()
        
        # We need a fallback if there's no data, but database.py pre-populates it.
        if not keywords:
            keywords = [('code', 'Intended Task'), ('video', 'Distraction')]
            
        self.keywords_list = keywords
        df_keywords = pd.DataFrame(keywords, columns=['phrase', 'category'])
        
        # TF-IDF and Naive Bayes pipeline with ngram range 1-2 and sublinear tf
        self.model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), MultinomialNB())
        self.model.fit(df_keywords['phrase'].str.lower(), df_keywords['category'])

    def predict(self, window_title: str, content_snippet: str = ""):
        """
        Predicts category based on window title and optional 70-word content snippet.
        Returns: (category, confidence_score, matched_keywords, railguard_overruled)
        """
        clean_title = (window_title or "").strip().lower()
        clean_snippet = (content_snippet or "").strip().lower()
        
        if not clean_title and not clean_snippet:
            return "Distraction", 0.0, [], False

        # 1. Title prediction
        title_cat = "Intended Task"
        title_conf = 0.5
        if self.model and clean_title:
            try:
                title_cat = self.model.predict([clean_title])[0]
                proba = self.model.predict_proba([clean_title])[0]
                title_conf = float(max(proba))
            except Exception:
                pass

        # If no snippet provided, return title prediction
        if not clean_snippet:
            return title_cat, title_conf, [], False

        # 2. Combined / Snippet analysis (Rail Guard)
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

        # 3. Keyword density scan across the 70-word snippet
        matched_keywords = []
        task_kw_count = 0
        dist_kw_count = 0

        for phrase, cat in self.keywords_list:
            p = phrase.lower().strip()
            if not p:
                continue
            if re.search(r'\b' + re.escape(p) + r'\b', combined_text):
                matched_keywords.append((p, cat))
                if cat == "Intended Task":
                    task_kw_count += 1
                elif cat == "Distraction":
                    dist_kw_count += 1

        # Check if railguard overruled title
        railguard_overruled = False
        final_category = snippet_cat
        final_conf = snippet_conf

        if dist_kw_count > task_kw_count and task_kw_count == 0:
            # Overruled to Distraction
            if title_cat == "Intended Task":
                railguard_overruled = True
            final_category = "Distraction"
            final_conf = max(snippet_conf, 0.85)
        elif task_kw_count > dist_kw_count and dist_kw_count == 0:
            # Overruled to Intended Task
            if title_cat == "Distraction":
                railguard_overruled = True
            final_category = "Intended Task"
            final_conf = max(snippet_conf, 0.85)

        return final_category, float(final_conf), matched_keywords, railguard_overruled

if __name__ == "__main__":
    classifier = WindowClassifier()
    print("Testing 'Visual Studio Code':", classifier.predict("Visual Studio Code"))
    print("Testing 'Work Research' with YouTube snippet:", classifier.predict("Work Research", "Watch live gaming videos and funny cat reels on youtube streaming platform"))
    print("Testing 'Google Chrome' with Python snippet:", classifier.predict("Google Chrome", "Python standard library documentation for asyncio and multiprocessing algorithms"))

