#!/usr/bin/env python3
"""
Better debugging approach using Python's import machinery
"""

import sys
import traceback
import importlib.util

def debug_import(module_name, package=None):
    """Import a module with full traceback on failure"""
    try:
        print(f"DEBUG: Attempting to import {module_name}")
        if package:
            module = importlib.import_module(module_name, package)
        else:
            module = importlib.import_module(module_name)
        print(f"DEBUG: Successfully imported {module_name}")
        return module
    except Exception as e:
        print(f"ERROR: Failed to import {module_name}")
        print(f"Exception: {e}")
        print(f"Exception type: {type(e).__name__}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("\nDetailed import traceback:")
        import_traceback = traceback.format_exception(*sys.exc_info())
        for line in import_traceback:
            print(line.strip())
        raise

# Set up environment
import os
os.environ['QT_API'] = 'pyside6'
os.environ.setdefault('ETS_TOOLKIT', 'qt')
os.environ['MPLBACKEND'] = 'Qt5Agg'

# Configure traits
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt'

# Create QApplication early
from PySide6.QtWidgets import QApplication
app = QApplication.instance()
if app is None:
    app = QApplication([])

# Now test the problematic imports with full debugging
print("=" * 50)
print("TESTING IMPORTS WITH FULL DEBUGGING")
print("=" * 50)

try:
    # Test each module that was failing
    debug_import('model.scan')
    debug_import('view.slice_viewer')  
    debug_import('view.pyloc')
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"\nFinal error: {e}")
    sys.exit(1)