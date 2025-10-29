#!/usr/bin/env python3
"""
Minimal test for slice_viewer import issue
"""

import os
import sys

# Set up environment exactly like the launcher
os.environ['QT_API'] = 'pyside6'
os.environ.setdefault('ETS_TOOLKIT', 'qt')
os.environ['MPLBACKEND'] = 'Qt5Agg'

# Configure traits
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt'

print("Testing critical imports one by one...")

try:
    print("1. Basic PySide6...")
    from PySide6.QtWidgets import QApplication
    print("   OK")
    
    print("2. Create QApplication...")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    print("   OK")
    
    print("3. matplotlib with Qt backend...")
    import matplotlib
    matplotlib.use('Qt5Agg')  # Force Qt backend
    import matplotlib.pyplot as plt
    print("   OK")
    
    print("4. matplotlib backends...")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    print("   OK")
    
    print("5. Full slice_viewer import...")
    sys.path.insert(0, os.getcwd())
    from view.slice_viewer import SliceViewWidget
    print("   SUCCESS!")
    
except Exception as e:
    print(f"FAILED at step: {e}")
    import traceback
    traceback.print_exc()