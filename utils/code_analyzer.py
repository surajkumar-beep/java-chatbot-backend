import re
import json
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict

# =========================================================
# LOAD ERROR PATTERNS
# =========================================================

ERRORS_PATH = Path(__file__).resolve().parent.parent / "data" / "common_java_errors.json"

with open(ERRORS_PATH, "r", encoding="utf-8") as f:
    ERROR_PATTERNS = json.load(f)

# =========================================================
# JAVAC OUTPUT PARSER (SINGLE BEST ROOT CAUSE)
# =========================================================

def parse_javac_output(output: str) -> List[Dict[str, str]]:
    """
    Parse javac errors and return ONE best root-cause suggestion
    """
    best_match = None
    best_score = -1

    for key, info in ERROR_PATTERNS.items():
        pattern = info.get("pattern")
        if not pattern:
            continue

        try:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            match = regex.search(output)
            if match:
                # Strong scoring logic
                score = 0
                score += len(pattern) * 5

                # Prioritize syntax killers
                if "';'" in match.group(0):
                    score += 500
                if "expected" in match.group(0).lower():
                    score += 200
                if "illegal start" in match.group(0).lower():
                    score += 150

                if score > best_score:
                    best_score = score
                    best_match = {
                        "id": key,
                        "title": info["title"],
                        "explanation": info["explanation"],
                        "fix_example": info.get("fix_example", ""),
                        "detail": match.group(0).strip()
                    }
        except re.error:
            continue

    if best_match:
        return [best_match]

    # Fallback
    if output.strip():
        return [{
            "id": "unknown_compile_error",
            "title": "❌ Compile Error",
            "explanation": "The compiler reported an error that didn't match known patterns.",
            "fix_example": "Check syntax carefully near the highlighted line.",
            "detail": output.strip()[:500]
        }]

    return []

# =========================================================
# PUBLIC CLASS NAME DETECTOR
# =========================================================

def find_public_class_name(code: str) -> str:
    m = re.search(r'public\s+class\s+([A-Za-z_]\w*)', code)
    if m:
        return m.group(1)
    m = re.search(r'class\s+([A-Za-z_]\w*)', code)
    return m.group(1) if m else "Main"

# =========================================================
# CODE SMELLS (ONLY WHEN CODE COMPILES)
# =========================================================

def detect_code_smells(code: str) -> List[Dict[str, str]]:
    issues = []

    if re.search(r'while\s*\(\s*true\s*\)', code):
        issues.append({
            "id": "infinite_loop",
            "title": "🔄 Infinite Loop",
            "explanation": "This loop runs forever unless explicitly stopped.",
            "fix_example": "Add a proper condition or a break statement.",
            "detail": "Detected while(true)"
        })

    return issues

# =========================================================
# RUNTIME ERROR ANALYZER (SEPARATE LOGIC)
# =========================================================

def analyze_runtime_output(output: str) -> List[Dict[str, str]]:
    exception = re.search(r'Exception in thread.*?(\w+Exception)', output)
    if exception:
        return [{
            "id": "runtime_exception",
            "title": f"🔴 {exception.group(1)}",
            "explanation": "A runtime exception occurred during execution.",
            "fix_example": "Check the stack trace and fix the failing line.",
            "detail": output.splitlines()[0]
        }]
    return []

# =========================================================
# MAIN ANALYZER
# =========================================================

def analyze_java_code(code: str):
    """
    Compile → Analyze → Run → Suggest
    """

    # Block Scanner input
    if "Scanner" in code and re.search(r'next(Int|Line|)\s*\(', code):
        return {
            "success": False,
            "compile_output": "",
            "runtime_output": "",
            "errors": [{
                "id": "requires_input",
                "title": "⌨️ User Input Required",
                "explanation": "Programs using Scanner cannot be executed automatically.",
                "fix_example": "Replace Scanner input with hardcoded values.",
                "detail": "Scanner detected"
            }]
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        class_name = find_public_class_name(code)
        java_file = tmp_path / f"{class_name}.java"
        java_file.write_text(code, encoding="utf-8")

        # Compile
        compile_proc = subprocess.run(
            ["javac", str(java_file)],
            capture_output=True,
            text=True
        )

        compile_output = compile_proc.stdout + compile_proc.stderr

        if compile_proc.returncode != 0:
            return {
                "success": False,
                "compile_output": compile_output,
                "runtime_output": "",
                "errors": parse_javac_output(compile_output)
            }

        # Run
        try:
            run_proc = subprocess.run(
                ["java", "-cp", str(tmp_path), class_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            runtime_output = run_proc.stdout + run_proc.stderr
            runtime_errors = analyze_runtime_output(runtime_output)

            if runtime_errors:
                return {
                    "success": False,
                    "compile_output": compile_output,
                    "runtime_output": runtime_output,
                    "errors": runtime_errors
                }

            smells = detect_code_smells(code)
            if smells:
                return {
                    "success": False,
                    "compile_output": compile_output,
                    "runtime_output": runtime_output,
                    "errors": smells[:1]
                }

            return {
                "success": True,
                "compile_output": compile_output,
                "runtime_output": runtime_output,
                "errors": []
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "compile_output": compile_output,
                "runtime_output": "",
                "errors": [{
                    "id": "timeout",
                    "title": "⏱️ Execution Timeout",
                    "explanation": "The program took too long to execute.",
                    "fix_example": "Check for infinite loops.",
                    "detail": "Timeout after 5 seconds"
                }]
            }
