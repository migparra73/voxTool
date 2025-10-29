__author__ = 'iped'

# Test version of slice_viewer with minimal imports to identify the problem

print("slice_viewer: Starting imports...")

try:
    print("slice_viewer: traits imports...")
    from traits.api import HasTraits, Instance, on_trait_change
    from traitsui.api import View, Item
    print("slice_viewer: traits OK")
    
    print("slice_viewer: mayavi imports...")
    from mayavi.core.ui.api import MayaviScene, MlabSceneModel, SceneEditor
    from mayavi import mlab
    print("slice_viewer: mayavi OK")
    
    print("slice_viewer: PySide6 imports...")
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel, QSizePolicy
    from PySide6.QtCore import Qt
    print("slice_viewer: PySide6 OK")
    
    print("slice_viewer: matplotlib imports...")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    
    # Use the correct matplotlib backend for PySide6
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    print("slice_viewer: matplotlib OK")
    
    print("slice_viewer: numpy imports...")
    import numpy as np
    print("slice_viewer: numpy OK")
    
    print("slice_viewer: All imports successful!")

except Exception as e:
    print(f"slice_viewer: Import failed: {e}")
    import traceback
    traceback.print_exc()
    raise

# Minimal class definitions to test
class SliceViewWidget(QWidget):
    def __init__(self, parent=None, scan=None):
        QWidget.__init__(self, parent)
        print("SliceViewWidget created")

class SliceView(FigureCanvas):
    def __init__(self, parent, data, axis, subplot):
        self.figure = Figure()
        FigureCanvas.__init__(self, self.figure)
        print("SliceView created")

class VoxelScene(HasTraits):
    scene = Instance(MlabSceneModel, ())
    view = View(Item('scene', editor=SceneEditor(scene_class=MayaviScene),
                     height=250, width=300, show_label=False),
                resizable=True)

    def __init__(self):
        HasTraits.__init__(self)
        print("VoxelScene created")

print("slice_viewer: Module loaded successfully!")