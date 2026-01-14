
# retrieval.py
import joblib
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def load_corpus(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)

def load_vectorizer(path: Path):
    return joblib.load(path)

def retrieve_answer(vectorizer, tfidf_matrix, corpus_df, query, k=1):
    q_vec = vectorizer.transform([query])
    sims = cosine_similarity(q_vec, tfidf_matrix)[0]
    top_idx = sims.argsort()[::-1][:k]
    return [{"question": corpus_df.iloc[i]["question"],
             "answer": corpus_df.iloc[i]["answer"],
             "score": float(sims[i])} for i in top_idx]
