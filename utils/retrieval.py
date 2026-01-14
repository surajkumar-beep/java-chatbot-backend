import joblib
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_corpus(path: Path) -> pd.DataFrame:
    """Load the corpus CSV file containing questions and answers"""
    return pd.read_csv(path)


def load_vectorizer(path: Path):
    """Load the trained TF-IDF vectorizer from disk"""
    return joblib.load(path)


def retrieve_answer(vectorizer, tfidf_matrix, corpus_df, query, k=1):
    """
    Retrieve the top k most similar answers from the corpus.
    
    Args:
        vectorizer: Trained TF-IDF vectorizer
        tfidf_matrix: Pre-computed TF-IDF matrix of corpus questions
        corpus_df: DataFrame containing questions and answers
        query: User's question string
        k: Number of top results to return
    
    Returns:
        List of dictionaries with question, answer, and similarity score
    """
    # Transform the query using the same vectorizer
    q_vec = vectorizer.transform([query])
    
    # Calculate cosine similarity between query and all corpus questions
    sims = cosine_similarity(q_vec, tfidf_matrix)[0]
    
    # Get indices of top k similar questions
    top_idx = sims.argsort()[::-1][:k]
    
    # Build result list with question, answer, and score
    results = []
    for i in top_idx:
        results.append({
            "question": corpus_df.iloc[i]["question"],
            "answer": corpus_df.iloc[i]["answer"],
            "score": float(sims[i])
        })
    
    return results
