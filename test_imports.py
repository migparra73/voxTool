#!/usr/bin/env python3
"""
Test individual imports from pyloc.py to identify the failing import
"""

import os
import sys

# Set up environment
os.environ['QT_API'] = 'pyside6'
os.environ.setdefault('ETS_TOOLKIT', 'qt')

print("Testing individual imports from pyloc.py...")

# Test basic imports first
try:
    import os
    import json
    print("✓ Basic Python imports (os, json)")
except Exception as e:
    print(f"✗ Basic Python imports failed: {e}")
    sys.exit(1)

# Test traits configuration
try:
    from traits.etsconfig.api import ETSConfig
    ETSConfig.toolkit = 'qt'
    print("✓ TraitsUI configuration")
except Exception as e:
    print(f"✗ TraitsUI configuration failed: {e}")
    sys.exit(1)

# Test PySide6 imports
try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                   QHBoxLayout, QLabel, QPushButton, QComboBox, 
                                   QSlider, QMessageBox, QFileDialog,
                                   QSizePolicy, QSplitter, QProgressBar, QCheckBox,
                                   QSpinBox, QDoubleSpinBox, QLineEdit, QGroupBox,
                                   QTabWidget, QScrollArea, QFrame, QTextEdit,
                                   QListWidget, QAbstractItemView, QListWidgetItem)
    print("✓ PySide6.QtWidgets imports")
except Exception as e:
    print(f"✗ PySide6.QtWidgets imports failed: {e}")
    sys.exit(1)

try:
    from PySide6.QtCore import Qt, QTimer, Signal, QItemSelectionModel
    print("✓ PySide6.QtCore imports")
except Exception as e:
    print(f"✗ PySide6.QtCore imports failed: {e}")
    sys.exit(1)

try:
    from PySide6.QtGui import QKeySequence, QIcon, QPixmap, QShortcut
    print("✓ PySide6.QtGui imports")
except Exception as e:
    print(f"✗ PySide6.QtGui imports failed: {e}")
    sys.exit(1)

# Test model imports
try:
    sys.path.insert(0, os.getcwd())
    from model.scan import CT
    print("✓ model.scan import")
except Exception as e:
    print(f"✗ model.scan import failed: {e}")

# Test slice viewer import
try:
    from view.slice_viewer import SliceViewWidget
    print("✓ view.slice_viewer import")
except Exception as e:
    print(f"✗ view.slice_viewer import failed: {e}")

# Test Mayavi imports
try:
    from mayavi.core.ui.api import MayaviScene, MlabSceneModel, SceneEditor
    print("✓ mayavi.core.ui.api imports")
except Exception as e:
    print(f"✗ mayavi.core.ui.api imports failed: {e}")

try:
    from mayavi import mlab
    print("✓ mayavi.mlab import")
except Exception as e:
    print(f"✗ mayavi.mlab import failed: {e}")

# Test traits API imports
try:
    from traits.api import HasTraits, Instance, on_trait_change
    print("✓ traits.api imports")
except Exception as e:
    print(f"✗ traits.api imports failed: {e}")

try:
    from traitsui.api import View, Item
    print("✓ traitsui.api imports")
except Exception as e:
    print(f"✗ traitsui.api imports failed: {e}")

# Test other imports
try:
    import random
    import numpy as np
    import logging
    import yaml
    import re
    from datetime import datetime
    from collections import OrderedDict
    print("✓ Other standard library imports")
except Exception as e:
    print(f"✗ Other imports failed: {e}")

print("\nAll import tests completed!")