import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import re
import pytest

def test_parse_error():
    """Test that all error patterns compile correctly"""
    errors_path = Path(__file__).resolve().parent.parent / "data" / "common_java_errors.json"
    
    # Load error patterns
    with open(errors_path, "r", encoding="utf-8") as f:
        errors = json.load(f)
    
    # Test each pattern
    for key, value in errors.items():
        pattern = value.get("pattern", "")
        
        # Skip empty patterns (some entries don't need regex matching)
        if not pattern:
            continue
        
        # Try to compile the regex pattern
        try:
            regex = re.compile(pattern)
            print(f"✅ Pattern '{key}' compiled successfully")
        except re.error as e:
            pytest.fail(f"❌ Bad regex for '{key}': {e}")


def test_error_structure():
    """Test that all error entries have required fields"""
    errors_path = Path(__file__).resolve().parent.parent / "data" / "common_java_errors.json"
    
    with open(errors_path, "r", encoding="utf-8") as f:
        errors = json.load(f)
    
    required_fields = ["pattern", "title", "explanation", "fix_example"]
    
    for key, value in errors.items():
        for field in required_fields:
            assert field in value, f"Error '{key}' missing field '{field}'"
        
        # Check that title and explanation are not empty
        assert value["title"].strip(), f"Error '{key}' has empty title"
        assert value["explanation"].strip(), f"Error '{key}' has empty explanation"


def test_pattern_matching():
    """Test that patterns match expected error messages"""
    errors_path = Path(__file__).resolve().parent.parent / "data" / "common_java_errors.json"
    
    with open(errors_path, "r", encoding="utf-8") as f:
        errors = json.load(f)
    
    # Test cases: (error_key, sample_error_message)
    test_cases = [
        ("null_pointer", "Exception in thread 'main' java.lang.NullPointerException"),
        ("array_index_out_of_bounds", "java.lang.ArrayIndexOutOfBoundsException: Index 5 out of bounds"),
        ("arithmetic_exception", "java.lang.ArithmeticException: / by zero"),
        ("cannot_find_symbol", "error: cannot find symbol"),
        ("missing_semicolon", "error: ';' expected"),
    ]
    
    for error_key, sample_message in test_cases:
        if error_key in errors:
            pattern = errors[error_key]["pattern"]
            if pattern:
                regex = re.compile(pattern)
                match = regex.search(sample_message)
                assert match, f"Pattern '{error_key}' should match: {sample_message}"
                print(f"✅ Pattern '{error_key}' matched correctly")


if __name__ == "__main__":
    # Run tests
    print("Running error pattern tests...\n")
    
    try:
        test_parse_error()
        print("\n" + "="*50)
        test_error_structure()
        print("\n" + "="*50)
        test_pattern_matching()
        print("\n" + "="*50)
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
