"""
Bump version in app/__init__.py using YY.MM.release_number scheme.
- If current YY.MM matches, increment release_number.
- If not, set release_number to 1.
"""
import re
from datetime import datetime

INIT_PATH = "app/__init__.py"
VERSION_PATTERN = re.compile(r'__version__\s*=\s*"(\d{2})\.(\d{2})\.(\d+)"')

def bump_version():
    now = datetime.utcnow()
    yy = now.year % 100
    mm = now.month
    new_prefix = f"{yy:02}.{mm:02}."
    with open(INIT_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    bumped = False
    for line in lines:
        m = VERSION_PATTERN.search(line)
        if m:
            old_yy, old_mm, old_rel = m.groups()
            if f"{old_yy}.{old_mm}." == f"{yy:02}.{mm:02}.":
                new_rel = int(old_rel) + 1
            else:
                new_rel = 1
            new_version = f'{yy:02}.{mm:02}.{new_rel}'
            new_line = f'__version__ = "{new_version}"
'
            new_lines.append(new_line)
            bumped = True
        else:
            new_lines.append(line)
    if bumped:
        with open(INIT_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"Bumped version to {new_version}")
    else:
        print("No version string found to bump.")

if __name__ == "__main__":
    bump_version()
