import sys
from pathlib import Path

# Allow importing utils/
sys.path.append(str(Path(__file__).resolve().parent.parent))

from flask import Flask, request, jsonify
from flask_cors import CORS

import joblib
import pandas as pd

from utils.retrieval import retrieve_answer
from utils.code_analyzer import analyze_java_code

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------
app = Flask(__name__)
CORS(app)  # 🔥 REQUIRED for Web Components

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
MODELS_DIR = BASE_DIR.parent / "models"

# --------------------------------------------------
# LOAD MODELS & DATA
# --------------------------------------------------
corpus = pd.read_csv(DATA_DIR / "corpus_java.csv")

vectorizer = joblib.load(MODELS_DIR / "tfidf_vectorizer.pkl")
tfidf_matrix = vectorizer.transform(
    corpus["question"].fillna("").tolist()
)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def looks_like_code(text: str) -> bool:
    """Detect if input resembles Java code"""
    patterns = [
        "class ",
        "public static void main",
        "System.out.println",
        "{", "}", ";"
    ]
    return len(text) > 30 and any(p in text for p in patterns)

# --------------------------------------------------
# API ROUTES
# --------------------------------------------------
@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Java Chatbot Backend is running"
    })

@app.route("/api/query", methods=["POST"])
def api_query():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "").strip()

    if not text:
        return jsonify({
            "type": "EMPTY_INPUT",
            "message": "Input cannot be empty"
        })

    # --------------------------------------------------
    # CODE ANALYSIS MODE
    # --------------------------------------------------
    if looks_like_code(text):
        analysis = analyze_java_code(text)

        return jsonify({
            "type": "CODE_ANALYSIS",
            "result": analysis
        })

    # --------------------------------------------------
    # QUESTION / ANSWER MODE
    # --------------------------------------------------
    results = retrieve_answer(
        vectorizer,
        tfidf_matrix,
        corpus,
        text,
        k=1
    )

    if results and results[0]["score"] >= 0.3:
        return jsonify({
            "type": "QA",
            "answer": results[0]["answer"],
            "confidence": results[0]["score"]
        })

    return jsonify({
        "type": "NO_ANSWER",
        "answer": "No relevant Java answer found."
    })

# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

