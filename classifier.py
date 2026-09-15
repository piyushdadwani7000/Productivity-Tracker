import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import database

class WindowClassifier:
    def __init__(self):
        self.model = None
        self.train_model()

    def train_model(self):
        """Fetches keywords and feedback from the database and retrains the model."""
        keywords = database.get_keywords()
        
        # We need a fallback if there's no data, but database.py pre-populates it.
        if not keywords:
            # Fallback minimum data
            keywords = [('code', 'Intended Task'), ('video', 'Distraction')]
            
        df_keywords = pd.DataFrame(keywords, columns=['phrase', 'category'])
        
        # In a full implementation, we'd also pull from classification_feedback
        # where users have confirmed or corrected labels, and append them to df_keywords.
        
        # We use a pipeline for TF-IDF and Naive Bayes
        self.model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB())
        self.model.fit(df_keywords['phrase'], df_keywords['category'])

    def predict(self, window_title):
        """Predicts the category of a window title. Returns (category, confidence_score)."""
        if not self.model or not window_title.strip():
            return "Distraction", 0.0 # Default fallback
            
        # The model expects a list/iterable
        prediction = self.model.predict([window_title])[0]
        
        # Get probability/confidence
        proba = self.model.predict_proba([window_title])[0]
        confidence = max(proba)
        
        return prediction, float(confidence)

if __name__ == "__main__":
    # Test
    classifier = WindowClassifier()
    print("Testing 'Visual Studio Code':", classifier.predict("Visual Studio Code"))
    print("Testing 'YouTube - Funny Cats':", classifier.predict("YouTube - Funny Cats"))
    print("Testing 'Some Random Website':", classifier.predict("Some Random Website"))
