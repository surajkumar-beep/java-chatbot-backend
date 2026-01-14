
def test_parse_error():
    from pathlib import Path
    import json, re
    errors = json.load(open("data/common_java_errors.json"))
    # ensure at least one pattern compiles
    for k, v in errors.items():
        try:
            re.compile(v["pattern"])
        except re.error:
            assert False, f"Bad regex for {k}"
