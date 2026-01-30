"""
Pylint and test coverage assertion tests.
Ensures code quality gates are enforced (Pylint ≥9.0/10, coverage ≥85%).
"""

import subprocess
import os
import sys


def venv_path(cmd):
    venv_bin = os.path.dirname(sys.executable)
    return os.path.join(venv_bin, cmd)

def test_pylint_score():
    """
    Tests that all app/ modules score ≥9.0/10 with pylint.

    Why: Enforces code quality for safety-critical system.

    Raises:
        AssertionError: If any file scores below 9.0
    """
    app_dir = os.path.join(os.path.dirname(__file__), '../app')
    pylint_path = venv_path('pylint')
    for fname in os.listdir(app_dir):
        # Only check app/ modules, not test files or conftest.py
        if not fname.endswith('.py') or fname == '__init__.py' or fname == 'conftest.py':
            continue
        path = os.path.join(app_dir, fname)
        result = subprocess.run([pylint_path, path, '--score', 'y', '--exit-zero'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.strip().startswith('Your code has been rated at'):
                score = float(line.split(' ')[6].split('/')[0])
                assert score >= 9.0, f"{fname} Pylint score {score} < 9.0"


def test_coverage():
    """
    Tests that test coverage is ≥85% for app/ modules.
    
    Why: Ensures all code paths are exercised by tests.
    
    Raises:
        AssertionError: If coverage is below 85%
    """
    coverage_path = venv_path('coverage')
    result = subprocess.run([coverage_path, 'report', '-m'], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if 'TOTAL' in line:
            percent = int(line.split()[-1].replace('%',''))
            assert percent >= 85, f"Test coverage {percent}% < 85%"
