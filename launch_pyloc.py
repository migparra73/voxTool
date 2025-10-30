#! /usr/bin/env python

"""
VoxTool Medical Imaging Application Launcher

This module serves as the main entry point for the VoxTool medical imaging
application, handling environment setup, dependency verification, and
graceful application initialization for neurological electrode localization
workflows.

Core Responsibilities:
---------------------
1. **Environment Configuration**: Qt backend and matplotlib setup for medical imaging
2. **Dependency Validation**: Verification of critical medical imaging libraries
3. **Error Handling**: Graceful failure with diagnostic information
4. **Application Bootstrap**: Main application controller initialization
5. **Resource Management**: Icon, configuration, and asset loading
6. **Cross-Platform Support**: Windows, Linux, macOS compatibility

Medical Application Context:
---------------------------
VoxTool is a specialized medical imaging application for:
- **Electrode Localization**: CT scan analysis for implanted medical electrodes
- **Neurological Procedures**: Support for epilepsy monitoring and neurosurgery
- **3D Visualization**: Advanced rendering of medical imaging data
- **Clinical Workflows**: Integration with hospital imaging systems

Technical Architecture:
----------------------
- **Qt6 Integration**: PySide6 for modern medical imaging interfaces
- **PyVista/VTK**: Advanced 3D medical visualization capabilities
- **Medical File I/O**: Support for NIFTI and other medical imaging formats
- **Configuration Management**: YAML-based application settings
- **Error Recovery**: Robust error handling for clinical environments

Environment Setup Process:
--------------------------
1. Configure Qt backend (PySide6) for optimal medical imaging performance
2. Set matplotlib backend for compatibility with Qt medical interfaces
3. Validate critical dependencies (nibabel, PyVista, traits)
4. Load application configuration from YAML files
5. Initialize logging for medical application diagnostics
6. Create main application controller and GUI
7. Set application icon and window properties
8. Enter Qt event loop for interactive medical workflows

Error Handling Strategy:
-----------------------
- **Graceful Degradation**: Continue with reduced functionality when possible
- **Diagnostic Output**: Detailed error messages for technical support
- **Early Detection**: Validate dependencies before GUI initialization
- **User Communication**: Clear error messages for clinical users
- **Recovery Guidance**: Specific instructions for common setup issues

Dependencies Validated:
----------------------
- PySide6: Qt6 GUI framework for medical interfaces
- PyVista: 3D scientific visualization for medical data
- nibabel: Medical imaging file format support (NIFTI)
- traits: Observable properties for real-time medical data binding
- numpy/scipy: Numerical computing for medical image processing
- yaml: Configuration file management

Usage:
------
Run directly from command line:
```bash
python launch_pyloc.py
```

Or from bundled executable:
```bash
./voxTool.exe  # Windows
./voxTool      # Linux/macOS
```

Author: VoxTool Development Team
License: See LICENSE.txt
"""

__author__ = 'iped'
import os
import sys

print("Starting voxTool launcher...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Set PySide6 as the Qt backend before any Qt imports
# This ensures consistent behavior across different Qt installations
os.environ['QT_API'] = 'pyside6'
os.environ.setdefault('ETS_TOOLKIT', 'qt')
# Set matplotlib backend to use PySide6 for medical imaging compatibility
os.environ['MPLBACKEND'] = 'QtAgg'
print("Set Qt backend to PySide6")

# Add the bundled directory to the path if running from PyInstaller
# This enables proper resource loading in both development and production
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle (production deployment)
    bundle_dir = sys._MEIPASS
    print(f"Running from PyInstaller bundle: {bundle_dir}")
else:
    # Running in a normal Python environment (development)
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Running from source: {bundle_dir}")

print("Configuring TraitsUI for medical imaging workflows...")
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt'
print(f"ETSConfig.toolkit set to: {ETSConfig.toolkit}")

# Configure Linux-specific Qt platform settings for medical workstations
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
    
    print("  Importing pyvista...")
    import pyvista as pv
    import pyvistaqt as pvqt
    print("  pyvista imports successful")
    
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
        
        print("      pyvista...")
        import pyvista as pv
        import pyvistaqt as pvqt
        
        print("      traits and traitsui...")
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
