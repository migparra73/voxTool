#! /usr/bin/env python

__author__ = 'iped'
import os
import sys

print("Starting voxTool launcher...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Set PySide6 as the Qt backend before any Qt imports
os.environ['QT_API'] = 'pyside6'
os.environ.setdefault('ETS_TOOLKIT', 'qt')
# Set matplotlib backend to use PySide6
os.environ['MPLBACKEND'] = 'QtAgg'
print("Set Qt backend to PySide6")

# Add the bundled directory to the path if running from PyInstaller
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
    print(f"Running from PyInstaller bundle: {bundle_dir}")
else:
    # Running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Running from source: {bundle_dir}")

print("Configuring TraitsUI...")
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt'
print(f"ETSConfig.toolkit set to: {ETSConfig.toolkit}")

# If linux, set the QT_QPA_PLATFORM environment variable to xcb
if os.name == 'posix':
    if 'QT_QPA_PLATFORM' not in os.environ:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'

print("Importing PySide6...")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    print("PySide6 imports successful")
    
    # Create QApplication early to avoid matplotlib Qt backend issues
    print("Creating QApplication...")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        print("QApplication created")
    else:
        print("Using existing QApplication")
        
except ImportError as e:
    print(f"ERROR: PySide6 import failed: {e}")
    sys.exit(1)

print("Importing application modules...")
try:
    print("  Importing model.scan...")
    from model.scan import CT
    print("  model.scan import successful")
    
    print("  Importing view.slice_viewer...")
    from view.slice_viewer import SliceViewWidget
    print("  view.slice_viewer import successful")
    
    print("  Importing mayavi...")
    from mayavi.core.ui.api import MayaviScene, MlabSceneModel, SceneEditor
    from mayavi import mlab
    print("  mayavi imports successful")
    
    print("  Importing traits...")
    from traits.api import HasTraits, Instance, on_trait_change
    from traitsui.api import View, Item
    print("  traits imports successful")
    
    print("  Importing view.pyloc...")
    try:
        print("    Testing pyloc imports step by step...")
        
        # Test the basic imports that pyloc.py does
        print("      traits configuration...")
        from traits.etsconfig.api import ETSConfig
        
        print("      PySide6 widgets...")
        from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                       QHBoxLayout, QLabel, QPushButton, QComboBox, 
                                       QSlider, QMessageBox, QFileDialog,
                                       QSizePolicy, QSplitter, QProgressBar, QCheckBox,
                                       QSpinBox, QDoubleSpinBox, QLineEdit, QGroupBox,
                                       QTabWidget, QScrollArea, QFrame, QTextEdit,
                                       QListWidget, QAbstractItemView, QListWidgetItem)
        
        print("      PySide6 core...")
        from PySide6.QtCore import Qt, QTimer, Signal, QItemSelectionModel
        
        print("      PySide6 gui...")
        from PySide6.QtGui import QKeySequence, QIcon, QPixmap, QShortcut
        
        print("      model.scan...")
        from model.scan import CT
        
        print("      slice_viewer...")
        from view.slice_viewer import SliceViewWidget
        
        print("      mayavi core...")
        from mayavi.core.ui.api import MayaviScene, MlabSceneModel, SceneEditor
        
        print("      mayavi mlab...")
        from mayavi import mlab
        
        print("      traits api...")
        from traits.api import HasTraits, Instance, on_trait_change
        
        print("      traitsui api...")
        from traitsui.api import View, Item
        
        print("      other imports...")
        import random
        import numpy as np
        import logging
        import yaml
        import re
        from datetime import datetime
        from collections import OrderedDict
        
        print("    All individual imports OK, now importing pyloc module...")
        from view.pyloc import PylocControl
        print("PylocControl import successful")
        
    except Exception as e:
        print(f"    ERROR in pyloc import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error during import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

import yaml

if __name__ == '__main__':
    print("In main block...")
    
    def resource_path(rel_path: str) -> str:
        """Return absolute path to resource supporting both dev and PyInstaller bundle."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, rel_path)

    print("Loading configuration...")
    config = None
    config_path = os.path.join(bundle_dir, 'config.yml')
    print(f"Looking for config at: {config_path}")
    
    # Fallback to current directory if not found in bundle
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
        print(f"Config not found, trying: {config_path}")
    
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found at {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print("Configuration loaded successfully")
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        sys.exit(1)
    
    print("Creating PylocControl...")
    try:
        controller = PylocControl(config)
        print("PylocControl created successfully")
    except Exception as e:
        print(f"ERROR: Failed to create PylocControl: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Set application/window icon after Qt app exists and main window has been created
    print("Setting application icon...")
    icon_path = resource_path(os.path.join('resources', 'voxTool.ico'))
    if os.path.exists(icon_path):
        try:
            QApplication.setWindowIcon(QIcon(icon_path))
            # Also set explicitly on the main window if available
            if hasattr(controller, 'window') and controller.window is not None:
                controller.window.setWindowIcon(QIcon(icon_path))
            print("Icon set successfully")
        except Exception as e:
            print(f"Warning: Failed to set icon: {e}")
    else:
        print(f"Icon not found at: {icon_path}")
    
    print("Starting application...")
    try:
        controller.exec_()
    except Exception as e:
        print(f"ERROR: Application execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
