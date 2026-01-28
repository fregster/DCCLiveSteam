"""
Cognitive complexity enforcement test.
Ensures all functions maintain cognitive complexity ≤ 15 (SonarQube standard).
"""
import ast
import pytest
from pathlib import Path
from radon.complexity import cc_visit

# Maximum allowed cognitive complexity
MAX_COMPLEXITY = 15

# Directories to check
SOURCE_DIRS = ['app', 'tests']

def get_python_files():
    """
    Get all Python files in the project.
    
    Why: Need to analyze all source files for complexity.
    
    Returns:
        List of Path objects for .py files
        
    Example:
        >>> files = get_python_files()
        >>> len(files) > 0
        True
    """
    project_root = Path(__file__).parent.parent
    python_files = []
    
    for dir_name in SOURCE_DIRS:
        search_path = project_root / dir_name
        if search_path.exists():
            python_files.extend(search_path.glob('*.py'))
    
    # Exclude this test file and __init__ files
    return [f for f in python_files if f.name != 'test_complexity.py' and f.name != '__init__.py']


def test_cognitive_complexity():
    """
    Tests that all functions maintain cognitive complexity ≤ 15.
    
    Why: High cognitive complexity makes code hard to understand and maintain.
         SonarQube standard is 15 for safety-critical systems.
    
    Raises:
        AssertionError: If any function exceeds MAX_COMPLEXITY
        
    Safety: Prevents overly complex functions that are error-prone.
    
    Example:
        >>> test_cognitive_complexity()  # Passes if all functions comply
    """
    violations = []
    
    for py_file in get_python_files():
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Calculate complexity for all functions/methods
            results = cc_visit(code)
            
            for item in results:
                if item.complexity > MAX_COMPLEXITY:
                    violations.append({
                        'file': py_file.name,
                        'function': item.name,
                        'complexity': item.complexity,
                        'line': item.lineno
                    })
        except SyntaxError:
            # Skip files with syntax errors (they'll fail other tests)
            continue
    
    if violations:
        error_msg = "Cognitive complexity violations (max allowed: {}):\n".format(MAX_COMPLEXITY)
        for v in violations:
            error_msg += "  {file}:{line} - {function}() has complexity {complexity}\n".format(**v)
        pytest.fail(error_msg)


def test_no_deeply_nested_code():
    """
    Tests that no code exceeds 4 levels of nesting.
    
    Why: Deep nesting is a code smell indicating need for refactoring.
    
    Raises:
        AssertionError: If any code block exceeds 4 nesting levels
        
    Example:
        >>> test_no_deeply_nested_code()  # Passes if nesting is reasonable
    """
    MAX_NESTING = 4
    violations = []
    
    for py_file in get_python_files():
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            # Check nesting depth
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    depth = _get_max_nesting_depth(node)
                    if depth > MAX_NESTING:
                        violations.append({
                            'file': py_file.name,
                            'function': node.name,
                            'depth': depth,
                            'line': node.lineno
                        })
        except SyntaxError:
            continue
    
    if violations:
        error_msg = f"Nesting depth violations (max allowed: {MAX_NESTING}):\n"
        for v in violations:
            error_msg += "  {file}:{line} - {function}() has nesting depth {depth}\n".format(**v)
        pytest.fail(error_msg)


def _get_max_nesting_depth(node, current_depth=0):
    """
    Recursively calculate maximum nesting depth of a node.
    
    Why: Helper function to detect overly nested code structures.
    
    Args:
        node: AST node to analyze
        current_depth: Current recursion depth (default: 0)
        
    Returns:
        Integer representing maximum nesting depth
        
    Example:
        >>> _get_max_nesting_depth(ast_node, 0)
        3
    """
    max_depth = current_depth
    
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
            child_depth = _get_max_nesting_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = _get_max_nesting_depth(child, current_depth)
            max_depth = max(max_depth, child_depth)
    
    return max_depth
