#!/usr/bin/env python3
"""
Advanced import debugging using import hooks
"""

import sys
import importlib.util
import importlib.machinery

class ImportDebugger:
    def __init__(self):
        self.original_import = __builtins__.__import__
        self.depth = 0
    
    def debug_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        indent = "  " * self.depth
        print(f"{indent}→ Importing: {name}")
        
        self.depth += 1
        try:
            result = self.original_import(name, globals, locals, fromlist, level)
            self.depth -= 1
            print(f"{indent}✓ Success: {name}")
            return result
        except Exception as e:
            self.depth -= 1
            print(f"{indent}✗ FAILED: {name} - {e}")
            raise
    
    def install(self):
        __builtins__.__import__ = self.debug_import
    
    def uninstall(self):
        __builtins__.__import__ = self.original_import

# Install the import debugger
debugger = ImportDebugger()
debugger.install()

try:
    # Set up environment
    import os
    os.environ['QT_API'] = 'pyside6'
    os.environ.setdefault('ETS_TOOLKIT', 'qt')
    
    # Now do the imports that were failing
    print("Testing with import hook debugging...")
    
    from view.slice_viewer import SliceViewWidget
    print("slice_viewer import successful!")
    
    from view.pyloc import PylocControl  
    print("pyloc import successful!")
    
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    debugger.uninstall()