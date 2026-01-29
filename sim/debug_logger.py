"""
debug_logger.py

Centralised logging for simulation events. Supports colour and timestamp output.
"""

import time

COLOURS = {
    'INFO': '\033[94m',
    'WARN': '\033[93m',
    'ERROR': '\033[91m',
    'ENDC': '\033[0m',
}

def log(level: str, message: str):
    ts = time.strftime('%H:%M:%S')
    colour = COLOURS.get(level, '')
    endc = COLOURS['ENDC'] if colour else ''
    print(f"{colour}[{level}] {ts} {message}{endc}")

def info(msg):
    log('INFO', msg)

def warn(msg):
    log('WARN', msg)

def error(msg):
    log('ERROR', msg)
