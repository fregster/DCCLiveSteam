"""
Test to enforce hardware abstraction: no direct hardware access outside actuators/ and sensors/.

Fails if 'machine.Pin', 'machine.ADC', or 'machine.PWM' are imported or used outside allowed modules.
"""
import os
import re
import pytest

ALLOWED_DIRS = ["app/actuators", "app/sensors"]
HARDWARE_CLASSES = ["Pin", "ADC", "PWM"]
HARDWARE_IMPORTS = ["machine.Pin", "machine.ADC", "machine.PWM"]


def is_allowed(path):
    return any(path.startswith(d) for d in ALLOWED_DIRS)

def test_no_direct_hardware_access():
    violations = []
    for root, _, files in os.walk("app"):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            rel_path = os.path.join(root, fname).replace("\\", "/")
            if is_allowed(rel_path):
                continue
            with open(rel_path, "r", encoding="utf-8") as f:
                code = f.read()
            # Remove comments (single-line and inline)
            code_no_comments = re.sub(r"(^|\s)#.*", "", code)
            for hw in HARDWARE_IMPORTS:
                if re.search(rf"import\s+{re.escape(hw)}|from\s+machine\s+import.*\b{hw.split('.')[-1]}\b", code_no_comments):
                    violations.append(f"{rel_path}: direct import of {hw}")
            for hw in HARDWARE_CLASSES:
                if re.search(rf"\b{hw}\s*\(", code_no_comments):
                    violations.append(f"{rel_path}: direct use of {hw}() constructor")
    assert not violations, "Direct hardware access found outside actuators/ and sensors/:\n" + "\n".join(violations)
