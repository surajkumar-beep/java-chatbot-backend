
from flask import Flask, request, render_template, jsonify
import joblib, os, json
from pathlib import Path
# Minimal imports; re-use notebook utilities after refactoring for production

app = Flask(__name__, template_folder="templates")

# load model and corpus (adjust BASE_DIR if needed)
BASE = Path(__file__).resolve().parents[1]
models_dir = BASE / "models"
data_dir = BASE / "data"
vectorizer = joblib.load(models_dir / "tfidf_vectorizer.pkl")
corpus = __import__("pandas").read_csv(data_dir / "corpus_java.csv")
# Note: for full logic, import your utils.code_analyzer and utils.retrieval after refactor

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/query", methods=["POST"])
def api_query():
    payload = request.json or {}
    text = payload.get("text", "")
    # For brevity, this is a placeholder; in production import functions written in utils/
    return jsonify({"status": "ok", "received": text})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
