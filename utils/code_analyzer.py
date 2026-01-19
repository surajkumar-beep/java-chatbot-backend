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

import subprocess
import tempfile
import shutil
from pathlib import Path

def analyze_java_code(code: str):
    """
    Analyze Java code: compile → run → code smells → ALL issues combined
    (NO duplicates, proper suggestions, SAFE for cloud)
    """

    # --------------------------------------------------
    # 0. ENVIRONMENT GUARD (CRITICAL FOR RENDER)
    # --------------------------------------------------
    if shutil.which("javac") is None or shutil.which("java") is None:
        return {
            "success": False,
            "compile_output": "",
            "runtime_output": "",
            "errors": [{
                "id": "java_not_available",
                "title": "🚫 Java Execution Not Available",
                "explanation": (
                    "This deployed server does not have Java (javac/java) installed. "
                    "Because of security and platform limits, code execution is disabled."
                ),
                "fix_example": (
                    "Run this code locally OR deploy using Docker with OpenJDK installed."
                ),
                "detail": "javac/java not found in server environment"
            }]
        }

    # --------------------------------------------------
    # 1. Check for input requirement
    # --------------------------------------------------
    if "Scanner" in code and ("nextInt()" in code or "nextLine()" in code or "next()" in code):
        return {
            "success": False,
            "compile_output": "",
            "runtime_output": "",
            "errors": [{
                "id": "requires_input",
                "title": "⌨️ Program Requires User Input",
                "explanation": "Uses Scanner to read user input, which cannot be automated here.",
                "fix_example": "Replace Scanner with hardcoded values or run locally.",
                "detail": "Scanner usage detected"
            }]
        }

    # --------------------------------------------------
    # 2. Always detect code smells
    # --------------------------------------------------
    code_smells = detect_code_smells(code)

    # --------------------------------------------------
    # 3. Write code to temporary file
    # --------------------------------------------------
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        class_name = find_public_class_name(code)
        java_file = tmp_path / f"{class_name}.java"
        java_file.write_text(code, encoding="utf-8")

        # --------------------------------------------------
        # 4. Compile
        # --------------------------------------------------
        compile_proc = subprocess.run(
            ["javac", str(java_file)],
            capture_output=True,
            text=True
        )
        compile_output = compile_proc.stdout + compile_proc.stderr

        # --------------------------------------------------
        # 5. Compilation failed → ONLY compile errors
        # --------------------------------------------------
        if compile_proc.returncode != 0:
            compile_errors = parse_javac_output(compile_output)

            unique_errors = []
            seen_ids = set()

            for err in compile_errors:
                eid = err.get("id")
                if eid not in seen_ids:
                    unique_errors.append(err)
                    seen_ids.add(eid)

            return {
                "success": False,
                "compile_output": compile_output,
                "runtime_output": "",
                "errors": unique_errors
            }

        # --------------------------------------------------
        # 6. Run program
        # --------------------------------------------------
        try:
            run_proc = subprocess.run(
                ["java", "-cp", str(tmp_path), class_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            runtime_output = run_proc.stdout + run_proc.stderr

            # --------------------------------------------------
            # 7. Runtime error analysis
            # --------------------------------------------------
            runtime_errors = analyze_runtime_output(runtime_output)

            # --------------------------------------------------
            # 8. Combine runtime + smells (no duplicates)
            # --------------------------------------------------
            all_errors = []
            seen_ids = set()

            for err in runtime_errors:
                eid = err.get("id")
                if eid not in seen_ids:
                    all_errors.append(err)
                    seen_ids.add(eid)

            for smell in code_smells:
                sid = smell.get("id")
                if sid not in seen_ids:
                    all_errors.append(smell)
                    seen_ids.add(sid)

            if all_errors:
                return {
                    "success": False,
                    "compile_output": compile_output,
                    "runtime_output": runtime_output,
                    "errors": all_errors[:3]
                }

            # --------------------------------------------------
            # 9. Perfect execution
            # --------------------------------------------------
            return {
                "success": True,
                "compile_output": compile_output,
                "runtime_output": runtime_output,
                "errors": []
            }

        # --------------------------------------------------
        # 10. Timeout handling
        # --------------------------------------------------
        except subprocess.TimeoutExpired:
            timeout_error = [{
                "id": "timeout",
                "title": "⏱️ Execution Timeout",
                "explanation": "Program exceeded 5-second limit (possible infinite loop).",
                "fix_example": "Add proper loop conditions or optimize code.",
                "detail": "Timeout after 5 seconds"
            }]

            combined = []
            seen_ids = set()

            for err in timeout_error:
                combined.append(err)
                seen_ids.add(err["id"])

            for smell in code_smells:
                if smell["id"] not in seen_ids:
                    combined.append(smell)

            return {
                "success": False,
                "compile_output": compile_output,
                "runtime_output": "Program execution timed out.",
                "errors": combined
            }
