"""
Docstring presence and format validation test.
Ensures all functions/classes have required docstrings (Why/Args/Returns/Raises/Safety/Example).
"""

import ast
import pytest
from pathlib import Path

REQUIRED_SECTIONS = ["Why:", "Args:", "Returns:", "Raises:", "Safety:", "Example:"]

# Directories to check
dirnames = ["app"]

def get_python_files():
    project_root = Path(__file__).parent.parent
    python_files = []
    for dirname in dirnames:
        d = project_root / dirname
        if d.exists():
            python_files.extend(d.glob("*.py"))
    return [f for f in python_files if f.name != "__init__.py"]



def _get_missing_sections(doc: str) -> list:
    """Return list of missing required docstring sections."""
    return [section for section in REQUIRED_SECTIONS if section not in doc]

def _check_node_docstring(node, py_file_name):
    """Check a single AST node for docstring compliance."""
    missing = []
    doc = ast.get_docstring(node)
    if not doc:
        missing.append(f"{py_file_name}:{node.lineno} {node.name} missing docstring")
    else:
        for section in _get_missing_sections(doc):
            missing.append(f"{py_file_name}:{node.lineno} {node.name} missing '{section}'")
    return missing

def check_file_for_docstring_violations(py_file):
    missing = []
    with open(py_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            missing.extend(_check_node_docstring(node, py_file.name))
    return missing

def test_docstring_presence_and_format():
    """
    Tests that all functions/classes have docstrings with required sections.

    Why: Required for safety-critical documentation and code review.

    Raises:
        AssertionError: If any function/class is missing docstring or required sections.
    """
    import os
    if not os.environ.get("RUN_DOCSTRING_TESTS", "0") == "1":
        pytest.skip("Docstring tests are disabled unless RUN_DOCSTRING_TESTS=1 is set.")
    all_missing = []
    for py_file in get_python_files():
        all_missing.extend(check_file_for_docstring_violations(py_file))
    if all_missing:
        msg = "Docstring format violations:\n" + "\n".join(all_missing)
        pytest.fail(msg)
