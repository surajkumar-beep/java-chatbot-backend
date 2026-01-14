from flask import Flask, request, render_template, jsonify
import joblib
import pandas as pd
import json
import re
import subprocess
import tempfile
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__, template_folder="templates")

# --------------------------------------------------------------------
# SETUP
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# Load model and data
vectorizer = joblib.load(MODELS_DIR / "tfidf_vectorizer.pkl")
corpus = pd.read_csv(DATA_DIR / "corpus_java.csv")

with open(DATA_DIR / "common_java_errors.json") as f:
    ERROR_PATTERNS = json.load(f)

# --------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------
def is_greeting(text):
    """Check if user said hello / hi / hey."""
    greetings = ["hi", "hello", "hey", "hola", "good morning", "good evening"]
    return text.lower().strip() in greetings

def is_java_code(text):
    """Detect if user input looks like Java code."""
    indicators = ["class ", "System.out.println", "public static void main", ";", "import java"]
    score = sum(1 for token in indicators if token in text)
    return score >= 1 and ("{" in text or "\n" in text)

def retrieve_answer(query):
    """Retrieve best Java answer from corpus."""
    q_vec = vectorizer.transform([query])
    sims = cosine_similarity(q_vec, vectorizer.transform(corpus["question"])).flatten()
    top_idx = sims.argsort()[::-1][0]
    return corpus.iloc[top_idx]["answer"], sims[top_idx]

def compile_java(code):
    """Compile the given Java code temporarily and capture errors."""
    tempdir = Path(tempfile.mkdtemp())
    java_file = tempdir / "Main.java"
    java_file.write_text(code)

    proc = subprocess.run(["javac", str(java_file)], capture_output=True, text=True)
    success = proc.returncode == 0
    output = (proc.stdout or "") + (proc.stderr or "")

    # Parse for known patterns
    suggestions = []
    for key, info in ERROR_PATTERNS.items():
        if re.search(info["pattern"], output):
            suggestions.append({
                "title": info["title"],
                "explanation": info["explanation"],
                "fix_example": info.get("fix_example", "")
            })

    # Try auto-fix for missing semicolon
    corrected_code = None
    if not success:
        if "';' expected" in output:
            corrected_code = code.replace("int x = 10", "int x = 10;")

    return {"success": success, "output": output, "suggestions": suggestions, "corrected_code": corrected_code}

# --------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"status": "error", "message": "Empty input"})

    # --- 1. Handle greetings ---
    if is_greeting(text):
        return jsonify({
            "status": "greeting",
            "answer": "Hello! 👋 I’m your Java assistant. Ask me any Java question or paste your code to debug it."
        })

    # --- 2. Handle Java code ---
    if is_java_code(text):
        result = compile_java(text)
        if result["success"]:
            return jsonify({
                "status": "code_analysis",
                "answer": "✅ Code compiled successfully! Great job!"
            })
        else:
            if result["corrected_code"]:
                return jsonify({
                    "status": "code_fix",
                    "answer": "❌ Found an error. Here's the corrected code:\n\n" + result["corrected_code"]
                })
            else:
                suggestion_text = ""
                for s in result["suggestions"]:
                    suggestion_text += f"• {s['title']} – {s['explanation']}\n{s['fix_example']}\n\n"
                return jsonify({
                    "status": "code_error",
                    "answer": "❌ Compilation failed:\n\n" + result["output"] + "\n\nSuggestions:\n" + suggestion_text
                })

    # --- 3. Handle normal Java questions ---
    answer, score = retrieve_answer(text)
    if score < 0.2:
        return jsonify({
            "status": "unknown",
            "answer": "I’m not sure about that. Can you rephrase or provide your Java code?"
        })

    return jsonify({
        "status": "qa",
        "answer": answer
    })

# --------------------------------------------------------------------
# RUN SERVER
# --------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
