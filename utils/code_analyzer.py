import re
import json
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict

# Load error patterns
ERRORS_PATH = Path(__file__).resolve().parent.parent / "data" / "common_java_errors.json"
with open(ERRORS_PATH, "r", encoding="utf-8") as f:
    ERROR_PATTERNS = json.load(f)

def parse_javac_output(output: str) -> List[Dict[str,str]]:
    """
    Parse javac output - SHOWS ONLY 1 BEST MATCH PER ERROR CATEGORY
    """
    scored_matches = []
    
    # Score matches by specificity (longer patterns = more specific)
    for key, info in ERROR_PATTERNS.items():
        pat = info["pattern"]
        if not pat:
            continue
            
        try:
            regex = re.compile(pat)
            m = regex.search(output)
            if m:
                # Score: pattern length + bonus for specific keywords
                score = len(pat) * 10 + (100 if any(word in m.group(0).lower() 
                    for word in ["incompatible types", "cannot convert", "lossy conversion"]) else 0)
                scored_matches.append({
                    "score": score,
                    "id": key,
                    "match": m.group(0),
                    "info": info
                })
        except re.error:
            continue
    
    # Sort by score (highest first) and deduplicate by category
    scored_matches.sort(key=lambda x: x["score"], reverse=True)
    seen_categories = set()
    matches = []
    
    for match in scored_matches:
        category = match["id"].split("_")[0]  # e.g., "type_mismatch", "incompatible_types" → "type"
        if category not in seen_categories:
            seen_categories.add(category)
            matches.append({
                "id": match["id"],
                "title": match["info"]["title"],
                "explanation": match["info"]["explanation"],
                "fix_example": match["info"].get("fix_example", ""),
                "detail": match["match"][:200] + "..." if len(match["match"]) > 200 else match["match"]
            })
    
    # Fallback if no matches
    if not matches and output.strip():
        matches.append({
            "id": "unknown",
            "title": "Unrecognized Error",
            "explanation": "Error message didn't match known patterns.",
            "fix_example": "Read the compiler output carefully and fix the syntax.",
            "detail": output.strip()[:500] + "..."
        })
    
    return matches[:1]  # Max 3 suggestions
    
    # IMPORTANT: return ONLY the single best match
    '''if matches:
        return [matches[0]]
    else:
        return []'''

def find_public_class_name(code: str) -> str:
    m = re.search(r'public\s+class\s+([A-Za-z_][A-Za-z0-9_]*)', code)
    if m:
        return m.group(1)
    m2 = re.search(r'class\s+([A-Za-z_][A-Za-z0-9_]*)', code)
    return m2.group(1) if m2 else "Main"

import re
def detect_code_smells(code: str):
    """40+ Common Mistakes + 35+ Best Practices Detection"""
    issues = []
    code_lower = code.lower()

    # ==================================================
    # 4. COMMON PROGRAMMING MISTAKES (40+ DETECTIONS)
    # ==================================================

    # 1. Off-by-one error
    if re.search(r'i\s*<=?\s*(length|size)', code):
        issues.append({
            "id": "1_off_by_one",
            "title": "📏 1. Off-by-One Error",
            "explanation": "Loop may run one time too many or too few. Use i < length for arrays/lists.",
            "fix": "for (int i = 0; i < array.length; i++)",
            "detail": "Check loop bounds around length/size"
        })

    # 2. Infinite loop mistake
    if re.search(r'while\s*\(\s*true\s*\)', code) or re.search(r'for\s*\(\s*;\s*;\s*\)', code):
        issues.append({
            "id": "2_infinite_loop",
            "title": "🔄 2. Infinite Loop",
            "explanation": "Loop runs forever without proper exit condition.",
            "fix": "Use explicit condition or break; ensure termination.",
            "detail": "Check while(true) or for(;;) usage"
        })

    # 3. Incorrect loop condition
    if re.search(r'for\s*\(\s*i\s*=\s*\d+\s*;\s*i\s*<\s*\d+\s*;\s*i\s*[\+\-]=?\s*-?\d+\)', code):
        issues.append({
            "id": "3_wrong_loop",
            "title": "🔀 3. Loop Condition",
            "explanation": "Loop bounds or step may not match requirement.",
            "fix": "Confirm start, end and increment (e.g., i++, i+=2).",
            "detail": "Verify loop condition and increment"
        })

    # 4. Wrong operator usage (==/!= with primitives vs objects)
    if re.search(r'(!=|==)\s*(int|double|float|long|short|byte)', code_lower):
        issues.append({
            "id": "4_wrong_op",
            "title": "⚠️ 4. Wrong Operator",
            "explanation": "Check operator usage for comparisons and assignments.",
            "fix": "Use == for primitives, .equals() for objects.",
            "detail": "Possible misuse of ==, != or = vs =="
        })

    # 5. Using == instead of .equals() (Strings)
    if 'String' in code and re.search(r'\b\w+\s*==\s*\w+\b', code):
        issues.append({
            "id": "5_string_equals",
            "title": "🚨 5. String == Comparison",
            "explanation": "Using == compares references instead of content for Strings.",
            "fix": "Use s1.equals(s2) or s1.equalsIgnoreCase(s2).",
            "detail": "String content comparison should use equals()"
        })

    # 6. Integer division mistake
    if re.search(r'\d+\s*/\s*\d+', code):
        issues.append({
            "id": "6_int_div",
            "title": "➗ 6. Integer Division",
            "explanation": "Integer division truncates decimal part (3/2 = 1).",
            "fix": "Use 3.0/2 or cast to double/float.",
            "detail": "Ensure correct type for division"
        })

    # 7. Floating-point precision mistake
    if re.search(r'(0\.1|0\.01|0\.001)\s*==', code):
        issues.append({
            "id": "7_float_prec",
            "title": "🔢 7. Float Precision",
            "explanation": "Exact equality with floating-point is unreliable.",
            "fix": "Use BigDecimal or compare with tolerance.",
            "detail": "Avoid == with non-integers like 0.1"
        })

    # 8. Ignoring operator precedence
    if re.search(r'\w+\s*\*\s*\+|[-+*/]\s*[-+*/]', code):
        issues.append({
            "id": "8_op_prec",
            "title": "📊 8. Operator Order",
            "explanation": "Complex expressions may be confusing without parentheses.",
            "fix": "Use explicit parentheses (a + b) * c.",
            "detail": "Clarify operator precedence"
        })

    # 9. Incorrect variable scope usage
    if re.search(r'{\s*\w+\s*=\s*[^;]*;\s*\w+\s*=\s*[^;]*;', code):
        issues.append({
            "id": "9_var_scope",
            "title": "📍 9. Variable Scope",
            "explanation": "Variables may be declared or used in wrong scope.",
            "fix": "Declare variables in the smallest necessary scope.",
            "detail": "Check variable lifetimes inside blocks"
        })

    # 10. Shadowing variables unintentionally
    if re.search(r'(int|double|float|long|String)\s+(\w+)\s*;[^\n]*\n[^\n]*(int|double|float|long|String)\s+\2\b', code):
        issues.append({
            "id": "10_shadow",
            "title": "🌑 10. Variable Shadowing",
            "explanation": "Inner variable hides outer variable with same name.",
            "fix": "Rename inner variable or avoid reuse.",
            "detail": "Shadowing can cause subtle bugs"
        })

    # 11. Using uninitialized logic values
    if re.search(r'boolean\s+(\w+)\s*;\s*if\s*\(\s*\1\s*\)', code):
        issues.append({
            "id": "11_uninit",
            "title": "🎭 11. Uninitialized Boolean",
            "explanation": "Boolean may be read before being initialized.",
            "fix": "Initialize boolean (e.g., boolean flag = false;).",
            "detail": "Check default values and initialization"
        })

    # 12. Hard-coded values (magic numbers)
    if re.search(r'\b(18|65|100|999|365|24|60|1024)\b', code):
        issues.append({
            "id": "12_magic",
            "title": "🎯 12. Magic Numbers",
            "explanation": "Hard-coded constants reduce readability and flexibility.",
            "fix": "Use named constants (final int ADULT_AGE = 18;).",
            "detail": "Replace numeric literals with constants"
        })

    # 13. Not handling null cases
    if re.search(r'\.get\(', code) and 'null' not in code_lower:
        issues.append({
            "id": "13_null_case",
            "title": "❓ 13. Null Handling",
            "explanation": "Method calls without null checks can cause NullPointerException.",
            "fix": "Check for null before dereferencing.",
            "detail": "Add if (obj != null) or use Optional"
        })

    # 14. Ignoring exception handling (try without catch/finally)
    if 'try' in code and len(re.findall(r'try\s*\{', code)) > len(re.findall(r'catch\s*\(', code)) + len(re.findall(r'finally\s*\{', code)):
        issues.append({
            "id": "14_no_except",
            "title": "⚠️ 14. Missing Exception Handling",
            "explanation": "try block without proper catch/finally can hide errors.",
            "fix": "Add catch or finally to handle exceptions.",
            "detail": "Ensure all try have catch/finally"
        })

    # 15. Catching generic Exception
    if re.search(r'catch\s*\(\s*Exception\s*\w*\s*\)', code):
        issues.append({
            "id": "15_generic_ex",
            "title": "🎣 15. Generic Exception",
            "explanation": "Catching Exception hides specific error types.",
            "fix": "Catch more specific exceptions (e.g., IOException).",
            "detail": "Use fine-grained exception handling"
        })

    # 16. Swallowing exceptions silently
    if re.search(r'catch\s*\([^)]*\)\s*\{\s*(//\s*TODO|//\s*ignore|//\s*ignored)?\s*\}', code):
        issues.append({
            "id": "16_swallow_ex",
            "title": "🤐 16. Swallowed Exception",
            "explanation": "Exceptions are caught but not logged or handled.",
            "fix": "Log, rethrow, or handle the exception meaningfully.",
            "detail": "Empty catch blocks hide problems"
        })

    # 17. Resource leak (not closing resources)
    if re.search(r'new\s+(FileInputStream|FileOutputStream|BufferedReader|Scanner|Connection)\s*\(', code) and not re.search(r'close\s*\(', code):
        issues.append({
            "id": "17_resource_leak",
            "title": "💧 17. Resource Leak",
            "explanation": "Opened resources are not closed properly.",
            "fix": "Use try-with-resources or ensure close() in finally.",
            "detail": "Check streams, readers, connections"
        })

    # 18. Memory leak via object references
    if re.search(r'static\s+List<|static\s+Map<|static\s+Set<', code):
        issues.append({
            "id": "18_memory_leak",
            "title": "🧠 18. Memory Leak Risk",
            "explanation": "Static collections can grow unbounded and hold references.",
            "fix": "Clear collections or avoid long-lived static state.",
            "detail": "Review lifecycle of static collections"
        })

    # 19. Inefficient data structure choice
    if 'ArrayList' in code and re.search(r'\.contains\(', code):
        issues.append({
            "id": "19_inefficient_ds",
            "title": "🐢 19. Inefficient Data Structure",
            "explanation": "ArrayList.contains() is O(n); may be slow for large data.",
            "fix": "Use HashSet or Map for faster lookup.",
            "detail": "Choose structure based on access pattern"
        })

    # 20. Wrong algorithm selection
    if 'bubble' in code_lower or 'selection sort' in code_lower:
        issues.append({
            "id": "20_wrong_algo",
            "title": "📉 20. Suboptimal Algorithm",
            "explanation": "Inefficient algorithms impact performance on big inputs.",
            "fix": "Use better algorithms (e.g., quicksort, mergesort).",
            "detail": "Avoid O(n^2) where O(n log n) exists"
        })

    # 21. Premature optimization mistake
    if 'micro-optim' in code_lower or 'optimiz' in code_lower and 'TODO' in code_lower:
        issues.append({
            "id": "21_premature_opt",
            "title": "🧪 21. Premature Optimization",
            "explanation": "Optimizing before measuring can complicate code.",
            "fix": "Write clear code first, optimize after profiling.",
            "detail": "Focus on correctness and clarity first"
        })

    # 22. Overcomplicated logic
    if code.count('if') > 5 and code.count('else') > 3 and code.count('&&') + code.count('||') > 4:
        issues.append({
            "id": "22_complex_logic",
            "title": "🧩 22. Overcomplicated Logic",
            "explanation": "Too many conditions make code hard to read and test.",
            "fix": "Split into smaller methods or use guard clauses.",
            "detail": "Refactor deep, complex conditions"
        })

    # 23. Code duplication
    if re.search(r'(.{20,})\s*\n.*\1', code, re.DOTALL):
        issues.append({
            "id": "23_duplication",
            "title": "📚 23. Code Duplication",
            "explanation": "Duplicate logic increases maintenance cost.",
            "fix": "Extract common logic into reusable methods.",
            "detail": "DRY: Don't Repeat Yourself"
        })

    # 24. Poor method naming
    if re.search(r'void\s+(doStuff|processData|handle|method\d+)\s*\(', code):
        issues.append({
            "id": "24_poor_method_name",
            "title": "🏷️ 24. Poor Method Name",
            "explanation": "Generic names do not express intent.",
            "fix": "Use descriptive names like calculateTotal, validateUser.",
            "detail": "Name should show method purpose"
        })

    # 25. Poor class design
    if re.search(r'class\s+(Manager|Helper|Util)\b', code) and code.count('public') > 10:
        issues.append({
            "id": "25_poor_class_design",
            "title": "🏗️ 25. Poor Class Design",
            "explanation": "God classes handle too many responsibilities.",
            "fix": "Split class into focused smaller classes.",
            "detail": "Avoid all-in-one manager/helper classes"
        })

    # 26. Violating single responsibility principle
    if re.search(r'(save|load|print|validate).*(save|load|print|validate)', code_lower):
        issues.append({
            "id": "26_srp_violation",
            "title": "🧱 26. SRP Violation",
            "explanation": "Class or method handles unrelated responsibilities.",
            "fix": "Separate concerns into different classes/methods.",
            "detail": "Each unit should have one reason to change"
        })

    # 27. Tight coupling between classes
    if re.search(r'new\s+[A-Z]\w+\s*\(', code) and '.getInstance(' in code:
        issues.append({
            "id": "27_tight_coupling",
            "title": "🔗 27. Tight Coupling",
            "explanation": "Classes depend directly on concrete implementations.",
            "fix": "Use interfaces/abstractions or dependency injection.",
            "detail": "Reduce direct new of dependencies"
        })

    # 28. Excessive use of static
    if code_lower.count('static') > 5:
        issues.append({
            "id": "28_static_abuse",
            "title": "⚡ 28. Excessive Static Use",
            "explanation": "Too many static members break OO design and testability.",
            "fix": "Use instance fields and dependency injection.",
            "detail": "Static state is hard to test and maintain"
        })

    # 29. Misusing inheritance instead of composition
    if re.search(r'class\s+\w+\s+extends\s+\w+', code) and 'implements' not in code:
        issues.append({
            "id": "29_inheritance_overuse",
            "title": "🧬 29. Inheritance Misuse",
            "explanation": "Inheritance used where composition may be better.",
            "fix": "Prefer composition over inheritance for reuse.",
            "detail": "Use has-a instead of is-a when appropriate"
        })

    # 30. Incorrect method overriding logic
    if '@Override' in code and re.search(r'@Override\s+public\s+\w+\s+\w+\(', code) and 'super.' not in code:
        issues.append({
            "id": "30_bad_override",
            "title": "🔁 30. Incorrect Override",
            "explanation": "Override may ignore required behavior of superclass.",
            "fix": "Call super.method() when necessary or document change.",
            "detail": "Verify contract of overridden methods"
        })

    # 31. Forgetting break in switch
    if re.search(r'switch\s*\([^)]*\)\s*\{([^}]*)\bcase\b[^:]*:[^b]*\n\s*case\b', code):
        issues.append({
            "id": "31_switch_break",
            "title": "🧯 31. Missing break in switch",
            "explanation": "Missing break causes fall-through to next case.",
            "fix": "Add break at the end of each case unless intentional.",
            "detail": "Review switch cases for fall-through"
        })

    # 32. Modifying collection while iterating
    if re.search(r'for\s*\(\s*\w+\s*:\s*\w+\s*\)\s*\{[^}]*\.\s*(add|remove|put)\s*\(', code):
        issues.append({
            "id": "32_concurrent_mod",
            "title": "🌀 32. Modify While Iterating",
            "explanation": "Changing collection during iteration can throw ConcurrentModificationException.",
            "fix": "Use iterator.remove() or collect changes separately.",
            "detail": "Avoid structural changes inside for-each"
        })

    # 33. Using mutable objects as map keys
    if re.search(r'Map<\s*List|Map<\s*Set|Map<\s*ArrayList', code):
        issues.append({
            "id": "33_mutable_key",
            "title": "🔑 33. Mutable Map Keys",
            "explanation": "Mutable keys can break Map contracts.",
            "fix": "Use immutable keys (String, Integer, custom immutable).",
            "detail": "Avoid mutable objects as keys"
        })

    # 34. Incorrect equals–hashCode implementation
    if ('equals(' in code and 'hashCode(' not in code) or ('hashCode(' in code and 'equals(' not in code):
        issues.append({
            "id": "34_equals_hash",
            "title": "⚖️ 34. equals/hashCode",
            "explanation": "Overriding only one breaks collections behavior.",
            "fix": "Override equals() and hashCode() together.",
            "detail": "Maintain consistency for hashed collections"
        })

    # 35. Ignoring thread safety
    if 'Thread' in code and 'synchronized' not in code and 'Executor' not in code:
        issues.append({
            "id": "35_thread_safety",
            "title": "🧵 35. Thread Safety",
            "explanation": "Shared mutable state across threads can cause bugs.",
            "fix": "Use synchronization, locks or thread-safe structures.",
            "detail": "Identify shared data in multithreaded code"
        })

    # 36. Race condition
    if re.search(r'count\s*\+\+|counter\s*\+\+', code) and 'synchronized' not in code:
        issues.append({
            "id": "36_race_condition",
            "title": "🏎️ 36. Race Condition",
            "explanation": "Non-atomic updates from multiple threads cause inconsistent state.",
            "fix": "Use AtomicInteger, synchronization or locks.",
            "detail": "Protect shared counters"
        })

    # 37. Deadlock risk
    if re.findall(r'synchronized\s*\(\s*\w+\s*\)', code) and code.count('synchronized') > 1:
        issues.append({
            "id": "37_deadlock",
            "title": "⛓️ 37. Deadlock Risk",
            "explanation": "Multiple locks acquired in different orders can deadlock.",
            "fix": "Define consistent locking order; minimize nested locks.",
            "detail": "Review nested synchronized blocks"
        })

    # 38. Improper synchronization
    if 'volatile' in code and 'synchronized' not in code and 'Atomic' not in code:
        issues.append({
            "id": "38_bad_sync",
            "title": "🧷 38. Improper Synchronization",
            "explanation": "volatile alone may not guarantee atomicity.",
            "fix": "Use proper synchronization or concurrent utilities.",
            "detail": "Ensure compound actions are atomic"
        })

    # 39. Blocking in main/UI thread
    if re.search(r'(Thread\.sleep|wait\()', code) and re.search(r'public\s+static\s+void\s+main', code):
        issues.append({
            "id": "39_blocking_main",
            "title": "⏱️ 39. Blocking Main Thread",
            "explanation": "Blocking main or UI thread freezes the application.",
            "fix": "Move blocking operations to background threads.",
            "detail": "Avoid sleep/wait on main/UI threads"
        })

    # 40. Misusing concurrency utilities
    if 'ExecutorService' in code and 'shutdown' not in code:
        issues.append({
            "id": "40_bad_concurrency_utils",
            "title": "🧰 40. Concurrency Utility Misuse",
            "explanation": "ExecutorService not shutdown causes resource leak.",
            "fix": "Call shutdown()/shutdownNow() when done.",
            "detail": "Always terminate executors"
        })

    # 41. Assuming execution order in threads
    if 'Thread.sleep' in code and 'join(' in code:
        issues.append({
            "id": "41_thread_order",
            "title": "🔀 41. Thread Order Assumption",
            "explanation": "Relying on timing for order is fragile.",
            "fix": "Use join(), latches, barriers instead of arbitrary sleep.",
            "detail": "Use synchronization primitives for ordering"
        })

    # 42. Not validating user input
    if 'Scanner' in code and 'nextLine' in code and 'if' not in code:
        issues.append({
            "id": "42_no_input_validation",
            "title": "🛂 42. No Input Validation",
            "explanation": "User input used without checks may cause errors or security issues.",
            "fix": "Validate format, range and sanitize input.",
            "detail": "Add checks after reading from Scanner"
        })

    # 43. Trusting external data blindly
    if re.search(r'HttpURLConnection|URL\s*\(', code) and 'validate' not in code_lower:
        issues.append({
            "id": "43_trust_external",
            "title": "🌐 43. Trusting External Data",
            "explanation": "Network/file data can be malformed or malicious.",
            "fix": "Validate and sanitize all external data.",
            "detail": "Add checks for responses and payloads"
        })

    # 44. Incorrect file path handling
    if re.search(r'new\s+File\s*\(\s*".*"\s*\)', code):
        issues.append({
            "id": "44_file_path",
            "title": "📁 44. Hard-coded File Path",
            "explanation": "Absolute or hard-coded paths reduce portability.",
            "fix": "Use relative paths or configuration.",
            "detail": "Avoid environment-specific paths"
        })

    # 45. Platform-dependent assumptions
    if re.search(r'\\\\', code) or 'C:\\\\' in code:
        issues.append({
            "id": "45_platform_dependent",
            "title": "🖥️ 45. Platform Dependent Code",
            "explanation": "OS-specific paths or separators break portability.",
            "fix": "Use File.separator or Paths API.",
            "detail": "Remove Windows-only assumptions"
        })

    # 46. Ignoring edge cases
    if 'TODO' in code and 'edge' in code_lower:
        issues.append({
            "id": "46_edge_cases",
            "title": "🧊 46. Ignored Edge Cases",
            "explanation": "Missing edge-case handling causes crashes or bugs.",
            "fix": "Handle empty, null, min/max, and boundary inputs.",
            "detail": "Finish TODOs for edge conditions"
        })

    # 47. Lack of input boundary checks
    if re.search(r'(for|while)\s*\([^)]*length[^)]*\)', code) and 'if' not in code:
        issues.append({
            "id": "47_bounds_check",
            "title": "📐 47. Missing Bounds Check",
            "explanation": "No validation of index ranges can cause exceptions.",
            "fix": "Validate indexes before array/list access.",
            "detail": "Check 0 <= index < length"
        })

    # 48. Poor error messages
    if re.search(r'System\.out\.println\("Error"\)', code):
        issues.append({
            "id": "48_poor_error_msg",
            "title": "📢 48. Poor Error Messages",
            "explanation": "Generic messages make debugging difficult.",
            "fix": "Include context details in error messages.",
            "detail": "Describe what went wrong and where"
        })

    # 49. Logging sensitive data
    if re.search(r'password|secret|token', code_lower) and re.search(r'System\.out\.println|logger\.info|log\.info', code_lower):
        issues.append({
            "id": "49_sensitive_logging",
            "title": "🔐 49. Logging Sensitive Data",
            "explanation": "Sensitive info in logs is a security risk.",
            "fix": "Mask or avoid logging secrets.",
            "detail": "Remove credentials from logs"
        })

    # 50. Ignoring performance bottlenecks
    if re.search(r'for\s*\(.*\)\s*\{[^}]*StringBuilder', code, re.DOTALL):
        issues.append({
            "id": "50_perf_bottleneck",
            "title": "🚦 50. Performance Bottleneck Risk",
            "explanation": "Heavy operations in large loops may be slow.",
            "fix": "Optimize hot paths after profiling.",
            "detail": "Beware nested loops and heavy work"
        })

    # 51. Not writing unit tests
    if 'JUnit' not in code and '@Test' not in code and 'assert' not in code_lower:
        issues.append({
            "id": "51_no_tests",
            "title": "🧪 51. No Unit Tests",
            "explanation": "Lack of tests reduces confidence in changes.",
            "fix": "Add JUnit tests for key logic and edge cases.",
            "detail": "Start with tests for core methods"
        })

    # 52. Overfitting logic to sample data
    if 'hardcode' in code_lower or 'specific case' in code_lower:
        issues.append({
            "id": "52_overfitting",
            "title": "🎯 52. Overfitted Logic",
            "explanation": "Logic tailored only to known examples may fail in general.",
            "fix": "Generalize rules and test with varied inputs.",
            "detail": "Avoid assumptions from few samples"
        })

    # ==================================================
    # 5. BEST PRACTICES (35+ DETECTIONS)
    # ==================================================

    # 1. Follow consistent naming conventions
    if re.search(r'\b(int|String|double|float|long)\s+[A-Z]{2,}\b', code):
        issues.append({
            "id": "bp_1_naming_convention",
            "title": "✅ BP1: Naming Conventions",
            "explanation": "Variable names should follow camelCase, classes PascalCase.",
            "fix": "Rename to userName, totalAmount, etc.",
            "detail": "Maintain consistent naming style"
        })

    # 2. Write clean and readable code
    if '\t' in code or re.search(r'\s{8,}', code):
        issues.append({
            "id": "bp_2_clean_code",
            "title": "✅ BP2: Readable Code",
            "explanation": "Mixed indentation or long lines hurt readability.",
            "fix": "Use consistent indentation and line length.",
            "detail": "Format code with an auto-formatter"
        })

    # 3. Use meaningful variable and method names
    if re.search(r'\b(int|double|String)\s+[ijk]\b', code):
        issues.append({
            "id": "bp_3_meaningful_names",
            "title": "✅ BP3: Meaningful Names",
            "explanation": "Single-letter names hide intent (outside simple loops).",
            "fix": "Use names like index, count, total.",
            "detail": "Explain purpose via naming"
        })

    # 4. Keep methods small and focused
    if re.search(r'void\s+\w+\s*\([^)]*\)\s*\{(.|\n){200,}\}', code):
        issues.append({
            "id": "bp_4_small_methods",
            "title": "✅ BP4: Small Methods",
            "explanation": "Very long methods are hard to read and test.",
            "fix": "Extract smaller helper methods.",
            "detail": "Aim for single responsibility per method"
        })

    # 5. Follow single responsibility principle
    if re.search(r'public\s+class\s+\w+.*\{(.|\n){400,}\}', code):
        issues.append({
            "id": "bp_5_srp",
            "title": "✅ BP5: SRP",
            "explanation": "Large classes often mix responsibilities.",
            "fix": "Split into cohesive classes.",
            "detail": "One reason to change per class"
        })

    # 6. Avoid code duplication (DRY principle)
    if re.search(r'(.{30,})\n.*\1', code):
        issues.append({
            "id": "bp_6_dry",
            "title": "✅ BP6: DRY",
            "explanation": "Repeated code makes maintenance harder.",
            "fix": "Extract common code into methods.",
            "detail": "Refactor repeated blocks"
        })

    # 7. Prefer composition over inheritance
    if 'extends' in code and code.count('extends') > 1:
        issues.append({
            "id": "bp_7_composition",
            "title": "✅ BP7: Composition",
            "explanation": "Deep inheritance hierarchies are fragile.",
            "fix": "Use composition where suitable.",
            "detail": "Favor has-a relationships"
        })

    # 8. Program to interfaces, not implementations
    if re.search(r'ArrayList<|HashMap<|HashSet<', code) and 'List<' not in code and 'Map<' not in code:
        issues.append({
            "id": "bp_8_interfaces",
            "title": "✅ BP8: Program to Interfaces",
            "explanation": "Using concrete types directly reduces flexibility.",
            "fix": "Declare as List, Map, Set types.",
            "detail": "Depend on abstractions"
        })

    # 9. Use access modifiers properly
    if re.search(r'class\s+\w+\s*\{[^{]*\b(\w+)\s+\w+\s*;', code) and 'private' not in code:
        issues.append({
            "id": "bp_9_access_modifiers",
            "title": "✅ BP9: Access Modifiers",
            "explanation": "Fields without modifiers are package-private by default.",
            "fix": "Use private and provide getters/setters if needed.",
            "detail": "Encapsulate fields by default"
        })

    # 10. Minimize mutable state
    if 'public' in code and 'static' in code and not re.search(r'final', code):
        issues.append({
            "id": "bp_10_mutable_state",
            "title": "✅ BP10: Mutable State",
            "explanation": "Global mutable state complicates reasoning.",
            "fix": "Use final where possible; avoid public mutable fields.",
            "detail": "Reduce shared state"
        })

    # 11. Use constants instead of magic numbers
    if re.search(r'\b(18|65|100|365|60|24|1024)\b', code):
        issues.append({
            "id": "bp_11_constants",
            "title": "✅ BP11: Constants",
            "explanation": "Constants improve clarity and reuse.",
            "fix": "Introduce final static constants.",
            "detail": "Replace literals with named constants"
        })

    # 12. Handle exceptions properly
    if 'catch' in code and 'printStackTrace' in code:
        issues.append({
            "id": "bp_12_exceptions",
            "title": "✅ BP12: Exception Handling",
            "explanation": "PrintStackTrace alone is not user-friendly.",
            "fix": "Log with context and rethrow or handle gracefully.",
            "detail": "Use logging framework for errors"
        })

    # 13. Catch specific exceptions only
    if 'catch (Exception' in code:
        issues.append({
            "id": "bp_13_specific_ex",
            "title": "✅ BP13: Specific Exceptions",
            "explanation": "Specific catches produce clearer handling.",
            "fix": "Catch IOException, SQLException, etc.",
            "detail": "Avoid broad Exception catches"
        })

    # 14. Use try-with-resources
    if re.search(r'new\s+(FileInputStream|FileOutputStream|BufferedReader|Scanner)\s*\(', code) and 'try (' not in code:
        issues.append({
            "id": "bp_14_try_with_resources",
            "title": "✅ BP14: Try-with-Resources",
            "explanation": "Automatic resource closing prevents leaks.",
            "fix": "Wrap resource in try (Resource r = …) { }.",
            "detail": "Prefer try-with-resources over finally-close"
        })

    # 15. Validate all external inputs
    if ('Scanner' in code or 'BufferedReader' in code) and 'validate' not in code_lower:
        issues.append({
            "id": "bp_15_validate_input",
            "title": "✅ BP15: Validate Input",
            "explanation": "External inputs must be checked for correctness.",
            "fix": "Validate format, range, and content.",
            "detail": "Never trust external sources blindly"
        })

    # 16. Fail fast on invalid conditions
    if 'assert' not in code_lower and 'IllegalArgumentException' not in code:
        issues.append({
            "id": "bp_16_fail_fast",
            "title": "✅ BP16: Fail Fast",
            "explanation": "Failing fast simplifies debugging and avoids bad state.",
            "fix": "Use checks and throw exceptions early.",
            "detail": "Validate preconditions at method start"
        })

    # 17. Write unit tests
    if '@Test' not in code and 'JUnit' not in code:
        issues.append({
            "id": "bp_17_unit_tests",
            "title": "✅ BP17: Unit Tests",
            "explanation": "Tests guard against regressions.",
            "fix": "Write JUnit tests for core logic.",
            "detail": "Test both happy path and failures"
        })

    # 18. Test edge cases explicitly
    if 'edge' not in code_lower and 'boundary' not in code_lower:
        issues.append({
            "id": "bp_18_edge_tests",
            "title": "✅ BP18: Edge Cases",
            "explanation": "Edge-case tests increase robustness.",
            "fix": "Add tests for min, max, empty, null.",
            "detail": "Cover corner cases in tests"
        })

    # 19. Use version control effectively
    if 'git' not in code_lower:
        issues.append({
            "id": "bp_19_version_control",
            "title": "✅ BP19: Version Control",
            "explanation": "Version control is critical for team work.",
            "fix": "Use Git commits with meaningful messages.",
            "detail": "Track changes in repository"
        })

    # 20. Write self-documenting code
    if re.search(r'//\s*complicated', code_lower):
        issues.append({
            "id": "bp_20_self_doc",
            "title": "✅ BP20: Self-Documenting",
            "explanation": "Complicated code indicates need for refactor.",
            "fix": "Refactor to clearer, simpler code.",
            "detail": "Code should explain itself"
        })

    # 21. Add comments only where necessary
    if code.count('//') > 20:
        issues.append({
            "id": "bp_21_comments",
            "title": "✅ BP21: Necessary Comments",
            "explanation": "Too many comments may hide unclear code.",
            "fix": "Keep comments for why, not what.",
            "detail": "Prefer clear code to excessive comments"
        })

    # 22. Follow standard code formatting
    if re.search(r'[^\n]{120,}', code):
        issues.append({
            "id": "bp_22_formatting",
            "title": "✅ BP22: Formatting",
            "explanation": "Very long lines are hard to read.",
            "fix": "Wrap lines and use formatter.",
            "detail": "Apply standard style (e.g., Google Java Style)"
        })

    # 23. Use logging instead of print statements
    if 'System.out.println' in code:
        issues.append({
            "id": "bp_23_logging",
            "title": "✅ BP23: Logging",
            "explanation": "Print statements are not suitable for production logging.",
            "fix": "Use a logging framework (java.util.logging, Log4j).",
            "detail": "Replace prints with logger calls"
        })

    # 24. Log meaningful messages
    if 'log.info("")' in code or 'logger.info("")' in code:
        issues.append({
            "id": "bp_24_meaningful_log",
            "title": "✅ BP24: Meaningful Logging",
            "explanation": "Empty or vague logs are not helpful.",
            "fix": "Include context and identifiers in logs.",
            "detail": "Log what happened and why"
        })

    # 25. Avoid premature optimization
    if 'TODO optimize' in code:
        issues.append({
            "id": "bp_25_no_premature_opt",
            "title": "✅ BP25: Avoid Premature Optimization",
            "explanation": "Marking premature optimization TODOs can clutter code.",
            "fix": "Focus on clarity; optimize after profiling.",
            "detail": "Measure before optimizing"
        })

    # 26. Optimize only after profiling
    if 'profile' in code_lower:
        issues.append({
            "id": "bp_26_profile",
            "title": "✅ BP26: Profile First",
            "explanation": "Use profiler to find real bottlenecks.",
            "fix": "Optimize only hot spots.",
            "detail": "Avoid guessing performance issues"
        })

    # 27. Choose appropriate data structures
    if 'ArrayList' in code and 'insert(0' in code:
        issues.append({
            "id": "bp_27_ds_choice",
            "title": "✅ BP27: Data Structures",
            "explanation": "ArrayList insert at front is costly.",
            "fix": "Use LinkedList or Deque for front insertions.",
            "detail": "Match structure to access pattern"
        })

    # 28. Use immutable objects when possible
    if 'final class' not in code and 'record ' not in code and 'immutable' not in code_lower:
        issues.append({
            "id": "bp_28_immutable",
            "title": "✅ BP28: Immutable Objects",
            "explanation": "Immutable objects simplify reasoning and concurrency.",
            "fix": "Use final fields and no setters.",
            "detail": "Design value objects as immutable"
        })

    # 29. Override equals and hashCode correctly
    if 'equals(' in code and 'hashCode(' in code:
        issues.append({
            "id": "bp_29_equals_hash",
            "title": "✅ BP29: equals/hashCode",
            "explanation": "Both methods provided, check they match fields.",
            "fix": "Ensure same fields in equals and hashCode.",
            "detail": "Keep contract consistent"
        })

    # 30. Follow SOLID principles
    if 'interface' in code and 'implements' in code:
        issues.append({
            "id": "bp_30_solid",
            "title": "✅ BP30: SOLID",
            "explanation": "Use interfaces and small focused classes.",
            "fix": "Apply SRP, OCP, LSP, ISP, DIP.",
            "detail": "Design with SOLID in mind"
        })

    # 31. Avoid tight coupling
    if 'new ' in code and 'interface' not in code:
        issues.append({
            "id": "bp_31_loose_coupling",
            "title": "✅ BP31: Loose Coupling",
            "explanation": "Direct instantiation overused.",
            "fix": "Use interfaces and dependency injection.",
            "detail": "Reduce hard-wired dependencies"
        })

    # 32. Keep classes cohesive
    if re.search(r'class\s+\w+\s*\{(.|\n){500,}\}', code):
        issues.append({
            "id": "bp_32_cohesion",
            "title": "✅ BP32: Cohesive Classes",
            "explanation": "Very large classes often lack cohesion.",
            "fix": "Split responsibilities into separate classes.",
            "detail": "Group related behavior together"
        })

    # 33. Handle nulls safely
    if 'null' in code_lower and 'Optional' not in code:
        issues.append({
            "id": "bp_33_null_safety",
            "title": "✅ BP33: Null Safety",
            "explanation": "Null checks should be explicit and consistent.",
            "fix": "Use Optional or guard clauses.",
            "detail": "Avoid unexpected NullPointerExceptions"
        })

    # 34. Use Optional where appropriate
    if 'Optional<' in code:
        issues.append({
            "id": "bp_34_optional",
            "title": "✅ BP34: Optional Usage",
            "explanation": "Optional improves API clarity for nullable values.",
            "fix": "Use Optional for return types, not fields.",
            "detail": "Avoid overusing Optional in fields"
        })

    # 35. Avoid deep nesting
    if code.count('if') > 4 and code.count('{') - code.count('}') > 3:
        issues.append({
            "id": "bp_35_deep_nesting",
            "title": "✅ BP35: Avoid Deep Nesting",
            "explanation": "Deeply nested code is hard to follow.",
            "fix": "Use early returns or extract methods.",
            "detail": "Flatten nested conditions"
        })

    # 36. Prefer early returns
    if 'return' in code and 'if' in code:
        issues.append({
            "id": "bp_36_early_return",
            "title": "✅ BP36: Early Returns",
            "explanation": "Guard clauses can simplify flow.",
            "fix": "Return early on invalid state.",
            "detail": "Reduce nesting where possible"
        })

    # 37. Encapsulate object state
    if re.search(r'public\s+(int|String|double|float|long|List<|Map<|Set<)\s+\w+\s*;', code):
        issues.append({
            "id": "bp_37_encapsulation",
            "title": "✅ BP37: Encapsulation",
            "explanation": "Public fields break invariants.",
            "fix": "Make fields private with accessors.",
            "detail": "Protect internal state"
        })

    # 38. Make dependencies explicit
    if re.search(r'new\s+\w+\s*\(', code) and '@Autowired' not in code:
        issues.append({
            "id": "bp_38_dependencies",
            "title": "✅ BP38: Explicit Dependencies",
            "explanation": "Hidden dependencies make code hard to test.",
            "fix": "Inject dependencies via constructor or DI.",
            "detail": "Avoid hidden global access"
        })

    # 39. Use dependency injection
    if '@Autowired' in code or 'Injector' in code:
        issues.append({
            "id": "bp_39_di",
            "title": "✅ BP39: Dependency Injection",
            "explanation": "DI frameworks decouple construction from use.",
            "fix": "Prefer constructor injection.",
            "detail": "Improve testability via DI"
        })

    # 40. Avoid static abuse
    if code_lower.count('static') > 3:
        issues.append({
            "id": "bp_40_static_abuse",
            "title": "✅ BP40: Avoid Static Abuse",
            "explanation": "Too much static code harms flexibility.",
            "fix": "Refactor static util logic into services.",
            "detail": "Limit static to pure utilities/constants"
        })

    # 41. Design for testability
    if 'new Scanner(System.in)' in code:
        issues.append({
            "id": "bp_41_testability",
            "title": "✅ BP41: Testability",
            "explanation": "Direct System.in usage makes testing harder.",
            "fix": "Inject input streams or use abstractions.",
            "detail": "Separate IO from logic"
        })

    # 42. Write modular code
    if 'package ' in code and code.count('class ') > 3:
        issues.append({
            "id": "bp_42_modular",
            "title": "✅ BP42: Modular Code",
            "explanation": "Split logic into multiple packages/modules.",
            "fix": "Group related classes into packages.",
            "detail": "Improve structure and reuse"
        })

    # 43. Follow layered architecture
    if re.search(r'Controller|Service|Repository', code):
        issues.append({
            "id": "bp_43_layered",
            "title": "✅ BP43: Layered Architecture",
            "explanation": "Separate presentation, business, and data layers.",
            "fix": "Keep layers independent.",
            "detail": "Avoid leaking persistence to UI"
        })

    # 44. Separate business logic from UI
    if 'JFrame' in code and 'calculate' in code_lower:
        issues.append({
            "id": "bp_44_separate_ui",
            "title": "✅ BP44: Separate UI/Logic",
            "explanation": "Business rules in UI classes reduce reuse.",
            "fix": "Move logic to service/domain classes.",
            "detail": "UI should delegate to services"
        })

    # 45. Handle concurrency explicitly
    if 'Thread' in code or 'ExecutorService' in code:
        issues.append({
            "id": "bp_45_concurrency",
            "title": "✅ BP45: Explicit Concurrency",
            "explanation": "Concurrent code needs clear synchronization.",
            "fix": "Use concurrent collections and proper locks.",
            "detail": "Document concurrency assumptions"
        })

    # 46. Use thread-safe constructs
    if 'ConcurrentHashMap' in code or 'CopyOnWriteArrayList' in code:
        issues.append({
            "id": "bp_46_thread_safe",
            "title": "✅ BP46: Thread-safe Constructs",
            "explanation": "Thread-safe collections simplify multithreading.",
            "fix": "Use concurrent variants when shared across threads.",
            "detail": "Pick appropriate concurrent structure"
        })

    # 47. Document public APIs
    if re.search(r'public\s+(class|interface|enum)\s+\w+', code) and '/**' not in code:
        issues.append({
            "id": "bp_47_docs",
            "title": "✅ BP47: API Documentation",
            "explanation": "Public APIs should have Javadoc.",
            "fix": "Add Javadoc for public classes and methods.",
            "detail": "Explain behavior and contracts"
        })

    # 48. Keep methods side-effect minimal
    if re.search(r'get\w+\s*\([^)]*\)\s*\{[^}]*set\w+\(', code):
        issues.append({
            "id": "bp_48_side_effects",
            "title": "✅ BP48: Side Effects",
            "explanation": "Getters should not modify state.",
            "fix": "Separate queries from commands.",
            "detail": "Avoid surprising side effects"
        })

    # 49. Clean up unused code
    if 'TODO remove' in code or 'deprecated' in code_lower:
        issues.append({
            "id": "bp_49_unused_code",
            "title": "✅ BP49: Remove Unused Code",
            "explanation": "Dead code confuses readers.",
            "fix": "Delete or archive unused methods/classes.",
            "detail": "Keep codebase lean"
        })

    # 50. Review code regularly
    if 'review' in code_lower:
        issues.append({
            "id": "bp_50_code_review",
            "title": "✅ BP50: Code Review",
            "explanation": "Reviews catch issues early.",
            "fix": "Use peer review or pull requests.",
            "detail": "Encourage regular reviews"
        })

    # 51. Refactor continuously
    if 'refactor' in code_lower:
        issues.append({
            "id": "bp_51_refactor",
            "title": "✅ BP51: Continuous Refactor",
            "explanation": "Regular refactoring keeps code healthy.",
            "fix": "Refactor small pieces frequently.",
            "detail": "Avoid large, risky rewrites"
        })

    return issues

def analyze_runtime_output(output: str):
    """Analyze runtime output for exceptions and errors - SINGLE BEST MATCH"""
    # Check for any Exception in output
    exception_match = re.search(r'Exception in thread "[^"]*" ([\w\.]+)', output)
    if exception_match:
        # Use parse_javac_output for runtime too (gets scored matches)
        runtime_matches = parse_javac_output(output)
        
        # CRITICAL: Return ONLY the single highest‑priority match
        if runtime_matches:
            return [runtime_matches[0]]  # Only best match!
        else:
            return [{
                "id": "runtime_exception",
                "title": f"🔴 {exception_match.group(1)}",
                "explanation": f"A runtime exception occurred: {exception_match.group(1)}",
                "fix_example": "Check the stack trace for the line number and fix the issue.",
                "detail": output.split('\n')[0]
            }]

    # Check for Error (not Exception)
    error_match = re.search(r'Error in thread "[^"]*" ([\w\.]+)', output)
    if error_match:
        return [{
            "id": "runtime_error",
            "title": f"🔴 {error_match.group(1)}",
            "explanation": f"A runtime error occurred: {error_match.group(1)}",
            "fix_example": "Check the stack trace for details.",
            "detail": output.split('\n')[0]
        }]

    return []

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
