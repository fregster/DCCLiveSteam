# Test Requirements for ESP32 Live Steam Control System

## Installation
```bash
pip install pytest pytest-cov pylint radon
```

## Running Tests

### All Tests with Coverage
```bash
pytest tests/ -v --cov=. --cov-report=term-missing -W error
```

### Individual Test Modules
```bash
pytest tests/test_physics.py -v -W error
pytest tests/test_config.py -v -W error
pytest tests/test_safety.py -v -W error
pytest tests/test_complexity.py -v -W error
```

### Linting
```bash
pylint *.py --rcfile=.pylintrc
```

## Coverage Requirements
- Minimum 85% line coverage
- All critical safety functions must have 100% coverage

## Quality Gates
All tests must pass before deployment:
- ✅ Zero test failures
- ✅ Zero warnings (pytest -W error)
- ✅ Pylint score ≥ 9.0/10
- ✅ Cognitive complexity ≤ 15 per function
- ✅ Test coverage ≥ 85%
