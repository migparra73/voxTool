#!/usr/bin/env python3
"""
Test slice_viewer.py import step by step
"""

import os
import sys

# Set up environment
os.environ['QT_API'] = 'pyside6'
os.environ.setdefault('ETS_TOOLKIT', 'qt')
os.environ['MPLBACKEND'] = 'Qt5Agg'

print("Testing slice_viewer.py imports step by step...")

try:
    print("1. Testing basic imports...")
    from traits.api import HasTraits, Instance, on_trait_change
    from traitsui.api import View, Item
    print("   ✓ traits imports")
    
    print("2. Testing mayavi imports...")
    from mayavi.core.ui.api import MayaviScene, MlabSceneModel, SceneEditor
    from mayavi import mlab
    print("   ✓ mayavi imports")
    
    print("3. Testing PySide6 imports...")
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel, QSizePolicy
    from PySide6.QtCore import Qt
    print("   ✓ PySide6 imports")
    
    print("4. Testing matplotlib imports...")
    import matplotlib.pyplot as plt
    print("   ✓ matplotlib.pyplot")
    
    from matplotlib.patches import Circle
    print("   ✓ matplotlib.patches.Circle")
    
    print("5. Testing matplotlib backend...")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    print("   ✓ matplotlib backend")
    
    from matplotlib.figure import Figure
    print("   ✓ matplotlib.figure")
    
    print("6. Testing numpy...")
    import numpy as np
    print("   ✓ numpy")
    
    print("7. All individual imports successful!")
    
    # Now try to import the actual file
    print("8. Testing full slice_viewer import...")
    sys.path.insert(0, os.getcwd())
    from view.slice_viewer import SliceViewWidget
    print("   ✓ slice_viewer import successful!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()