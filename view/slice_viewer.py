"""
VoxTool Medical Imaging Slice Viewer Module

This module provides 2D slice visualization capabilities for medical imaging data,
specifically designed for CT scan navigation and electrode contact localization.
Integrates matplotlib with PySide6 for interactive medical imaging workflows.

Core Components Overview:
------------------------
1. **SliceViewWidget**: Main container for multiple orthogonal slice views
2. **SliceView**: Individual 2D slice visualization with matplotlib integration

Medical Imaging Context:
-----------------------
This slice viewer is essential for medical electrode localization workflows:
- **Orthogonal Views**: Axial, sagittal, and coronal slice orientations
- **Cross-referencing**: Coordinate markers across all three planes
- **Interactive Navigation**: Real-time slice updates during point selection
- **Medical Standards**: Proper image orientation and intensity windowing

Key Features:
------------
- **Triple-Pane Layout**: Simultaneous axial, sagittal, coronal views
- **Coordinate Synchronization**: Cross-hair markers across all slices
- **System Theme Integration**: Respects dark/light theme preferences
- **Matplotlib Backend**: PySide6-compatible rendering for Qt integration
- **Memory Efficient**: On-demand slice extraction from 3D volumes

Technical Architecture:
----------------------
- Uses Qt splitter for resizable slice view panels
- Matplotlib FigureCanvas for high-performance 2D rendering
- Dynamic color theming based on system preferences
- Coordinate transformation for medical image orientation
- Circle overlays for electrode contact visualization

Dependencies:
------------
- matplotlib: 2D plotting and image display
- PySide6: Qt6 GUI framework and windowing
- numpy: Numerical array operations
- traits/traitsui: Observable properties (future integration)

Author: VoxTool Development Team
License: See LICENSE.txt
"""

__author__ = 'iped'

print("slice_viewer: Starting imports...")

try:
    print("slice_viewer: importing traits...")
    from traits.api import HasTraits, Instance, on_trait_change
    from traitsui.api import View, Item
    
    print("slice_viewer: importing PySide6...")
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel, QSizePolicy, QApplication
    from PySide6.QtCore import Qt
    
    print("slice_viewer: importing matplotlib...")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    
    # Use the correct matplotlib backend for PySide6
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    
    print("slice_viewer: importing numpy...")
    import numpy as np
    
    print("slice_viewer: all imports successful")
    
    print("slice_viewer: defining classes...")

except Exception as e:
    print(f"slice_viewer: import failed: {e}")
    import traceback
    traceback.print_exc()
    raise

print("slice_viewer: defining SliceViewWidget...")
class SliceViewWidget(QWidget):
    """
    Multi-pane medical imaging slice viewer for CT scan navigation.
    
    This widget provides simultaneous visualization of three orthogonal slice
    orientations (axial, sagittal, coronal) for comprehensive medical imaging
    analysis. Essential for electrode localization workflows where precise
    3D coordinate identification requires cross-referencing across planes.
    
    Key Features:
    ------------
    - **Orthogonal Views**: Three synchronized 2D slice orientations
    - **Coordinate Markers**: Cross-hair visualization across all planes  
    - **Responsive Layout**: Resizable panels with equal space distribution
    - **System Theming**: Automatic dark/light theme integration
    - **Real-time Updates**: Immediate slice updates during coordinate changes
    
    Medical Workflow Integration:
    ----------------------------
    1. Load CT scan volume data into the viewer
    2. Navigate through slices using coordinate updates
    3. Visualize electrode contact locations with circle markers
    4. Cross-reference positions across axial, sagittal, coronal views
    5. Support manual electrode contact identification workflows
    
    Layout Structure:
    ----------------
    ```
    ┌─────────────────────────────────┐
    │ File Label                      │
    ├─────────────────────────────────┤
    │ Axial View (Z-axis slices)      │
    ├─────────────────────────────────┤
    │ Sagittal View (X-axis slices)   │
    ├─────────────────────────────────┤
    │ Coronal View (Y-axis slices)    │
    └─────────────────────────────────┘
    ```
    
    Attributes:
    -----------
    label : QLabel
        Displays current CT scan filename
    views : list of SliceView
        Three orthogonal slice viewers [axial, sagittal, coronal]
    ct : CT object or None
        Reference to current CT scan data
    """

    def __init__(self, parent=None, scan=None):
        """
        Initialize the slice viewer widget with orthogonal views.
        
        Parameters:
        -----------
        parent : QWidget or None
            Parent widget for Qt hierarchy
        scan : CT object or None
            Medical scan data to visualize
            
        Notes:
        ------
        Creates three SliceView instances for different anatomical orientations:
        - Axis 0: Sagittal (left-right slicing)
        - Axis 1: Coronal (front-back slicing)  
        - Axis 2: Axial (top-bottom slicing)
        """
        QWidget.__init__(self, parent)
        self.label = QLabel('')
        data = scan.data if scan else None
        
        # Create three orthogonal slice views
        # Each uses subplot 111 (single plot per figure) for maximum image area
        self.views = [
            SliceView(self, data, axis=0, subplot=111),  # Sagittal view
            SliceView(self, data, axis=1, subplot=111),  # Coronal view
            SliceView(self, data, axis=2, subplot=111)   # Axial view
        ]

        # Create vertical splitter for equal space distribution
        splitter = QSplitter(Qt.Orientation.Vertical)
        for view in self.views:
            # Set minimum size and expansion policy for each view
            view.setMinimumSize(200, 200)
            view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            splitter.addWidget(view)

        # Set equal sizes for all views in the splitter (33% each)
        splitter.setSizes([100, 100, 100])

        self.ct = None
        
        # Use system theme colors automatically (removed hardcoded black palette)
        # This ensures compatibility with dark/light theme switching
        
        # Create main layout with file label and slice views
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(splitter)

        # Update geometry for proper matplotlib integration
        FigureCanvas.updateGeometry(self)
        print("slice_viewer: SliceView constructor complete")

    def set_coordinate(self, coordinate):
        """
        Update the displayed coordinate across all slice views.
        
        Parameters:
        -----------
        coordinate : array-like
            [x, y, z] coordinate in image voxel space
            
        Notes:
        ------
        Synchronizes all three orthogonal views to show the same 3D point,
        essential for electrode contact localization workflows.
        """
        for slice_view in self.views:
            slice_view.coordinate = coordinate

    def set_image(self, image):
        """
        Load new 3D image data into all slice views.
        
        Parameters:
        -----------
        image : numpy.ndarray
            3D medical imaging volume (typically CT scan data)
        """
        for slice_view in self.views:
            slice_view.set_image(image)

    def set_label(self,label):
        """
        Update the file label display.
        
        Parameters:
        -----------
        label : str
            Filename or description of current scan
        """
        self.label.setText('File: \n%s'%label)

    def update_slices(self):
        """
        Refresh all slice visualizations.
        
        Triggers plot updates across all three orthogonal views,
        typically called after coordinate or image data changes.
        """
        for slice_view in self.views:
            slice_view.plot()

print("slice_viewer: defining SliceView class...")
class SliceView(FigureCanvas):
    """
    Individual 2D slice visualization with matplotlib rendering.
    
    This class handles the display of single orthogonal slices from 3D medical
    imaging volumes. Provides high-performance rendering with coordinate markers
    and interactive features for medical imaging analysis.
    
    Key Features:
    ------------
    - **Matplotlib Integration**: High-quality 2D image rendering
    - **Coordinate Markers**: Circle overlays for electrode contact visualization
    - **System Theming**: Dynamic color adaptation for dark/light themes
    - **Memory Efficient**: On-demand slice extraction from 3D volumes
    - **Medical Orientation**: Proper anatomical view orientations
    
    Rendering Pipeline:
    ------------------
    1. Extract 2D slice from 3D volume at specified coordinate
    2. Apply proper medical image orientation (flip/transpose)
    3. Render with bone colormap for CT scan visualization
    4. Overlay coordinate marker circle with visibility
    5. Update display with system-appropriate theming
    
    Coordinate System:
    -----------------
    - Uses medical imaging voxel coordinates
    - Handles proper slice orientation for anatomical views
    - Supports circle marker positioning with radius scaling
    - Maintains aspect ratio for accurate spatial representation
    
    Attributes:
    -----------
    figure : matplotlib.figure.Figure
        Main figure object for rendering
    ax : matplotlib.axes.Axes
        Plotting axes with medical image display
    data : numpy.ndarray or None
        3D image volume for slice extraction
    axis : int
        Slice orientation axis (0=sagittal, 1=coronal, 2=axial)
    coordinate : numpy.ndarray
        Current [x, y, z] position for slice extraction and marker
    circ : matplotlib.patches.Circle or None
        Coordinate marker circle overlay
    """

    def __init__(self, parent, data, axis, subplot):
        """
        Initialize individual slice view with matplotlib backend.
        
        Parameters:
        -----------
        parent : QWidget
            Parent widget for Qt integration
        data : numpy.ndarray or None
            3D medical imaging volume
        axis : int
            Slice orientation axis (0, 1, or 2)
        subplot : int
            Matplotlib subplot specification (typically 111)
            
        Notes:
        ------
        Sets up matplotlib figure with system theme colors and optimized
        layout for medical imaging visualization. Removes margins to
        maximize image display area.
        """
        # Get system colors from Qt palette for theme integration
        if parent and hasattr(parent, 'palette'):
            palette = parent.palette()
        else:
            # Create a temporary widget to get default palette
            temp_widget = QWidget()
            palette = temp_widget.palette()
            
        # Extract color values and convert to matplotlib format (0-1 range)
        bg_color = palette.color(palette.ColorRole.Window)
        text_color = palette.color(palette.ColorRole.WindowText)
        bg_rgb = (bg_color.redF(), bg_color.greenF(), bg_color.blueF())
        text_rgb = (text_color.redF(), text_color.greenF(), text_color.blueF())
        
        # Create matplotlib figure with system background color and tight layout
        self.figure = Figure(facecolor=bg_rgb, edgecolor=text_rgb)
        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)
        
        # Initialize slice view properties
        self.data = data
        self.axis = axis
        self.coordinate = np.zeros((3,))  # Current coordinate position
        self.plotted_coordinate = np.zeros((3,))  # Last plotted coordinate
        self.radius = 1  # Marker circle radius
        self.plotted_radius = 1  # Last plotted radius
        self.subplot = subplot
        
        # Create subplot with system colors and no margins for maximum image area
        self.ax = self.figure.add_subplot(subplot)
        self.ax.set_facecolor(bg_rgb)
        
        # Remove all margins and padding to maximize image display space
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0, hspace=0, wspace=0)
        
        # Configure text colors for medical imaging compatibility
        self.ax.tick_params(colors=text_rgb)
        self.ax.xaxis.label.set_color(text_rgb)
        self.ax.yaxis.label.set_color(text_rgb)
        
        # Initialize coordinate marker
        self.circ = None
        
        # Set size policy for Qt integration
        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)

    def set_image(self, image):
        """
        Set the 3D image volume for slice extraction.
        
        Parameters:
        -----------
        image : numpy.ndarray
            3D medical imaging volume (typically CT scan data)
        """
        self.image = image

    def set_axis(self, axis):
        """
        Change the slice orientation axis.
        
        Parameters:
        -----------
        axis : int
            New slice axis (0=sagittal, 1=coronal, 2=axial)
        """
        self.axis = axis

    def plot(self):
        """
        Render the current 2D slice with coordinate markers.
        
        This method performs the complete rendering pipeline:
        1. Extract 2D slice from 3D volume at current coordinate
        2. Apply proper medical image orientation transforms
        3. Display with bone colormap optimized for CT scans
        4. Overlay coordinate marker circle at specified position
        5. Update display with current system theme colors
        
        Notes:
        ------
        - Uses 'bone' colormap optimized for CT scan visualization
        - Applies flipud and transpose for proper medical orientation
        - Scales marker circle radius based on slice axis for visibility
        - Handles dynamic theming for dark/light mode compatibility
        """
        # Return early if no image data or axis is available
        if self.axis is None or self.image is None:
            return
            
        # Get current system colors (may have changed since initialization)
        try:
            from PySide6.QtWidgets import QApplication, QWidget
            app = QApplication.instance()
            if app:
                # Create a temporary widget to access current palette
                temp_widget = QWidget()
                palette = temp_widget.palette()
                bg_color = palette.color(palette.ColorRole.Window)
                bg_rgb = (bg_color.redF(), bg_color.greenF(), bg_color.blueF())
            else:
                bg_rgb = (0, 0, 0)  # fallback to black
        except:
            bg_rgb = (0, 0, 0)  # fallback to black
            
        # Create slice plane specification for 3D volume extraction
        plot_plane = [slice(0, self.image.shape[i]) for i in range(3)]
        plot_plane[self.axis] = int(self.coordinate[self.axis])
        plot_plane_tuple = tuple(plot_plane)

        # Extract 2D slice and apply medical imaging orientation
        plotted_image = self.image[plot_plane_tuple]
        plotted_image = np.flipud(plotted_image.T)  # Standard medical orientation
        
        # Clear axes and configure for maximum image display area
        self.ax.cla()
        self.ax.set_position((0.0, 0.0, 1.0, 1.0))  # Use full figure area
        self.ax.axis('off')  # Turn off axes for clean medical image display
        self.ax.set_facecolor(bg_rgb)
        
        # Display image with bone colormap (optimized for CT scans)
        # aspect='auto' allows image to fill available space
        self._plot = self.ax.imshow(plotted_image, cmap=plt.get_cmap('bone'), 
                                   aspect='auto', interpolation='bilinear')
        
        # Add coordinate marker circle overlay
        # Calculate circle coordinates by removing the sliced axis
        circl_coords = list(self.coordinate)
        del circl_coords[self.axis]
        
        # Scale radius based on axis for optimal visibility
        radius = 10 if self.axis != 3 else 40

        # Apply coordinate transforms for proper marker positioning
        if self.axis != 2:
            # For sagittal and coronal views, flip Y coordinate
            circl_coords[0], circl_coords[1] = circl_coords[0], plotted_image.shape[0] - circl_coords[1]
        else:
            # For axial view, only flip Y coordinate
            circl_coords[1] = plotted_image.shape[0] - circl_coords[1]

        # Create and add coordinate marker circle
        circle_center = tuple(circl_coords)
        self.circ = Circle(circle_center, radius=radius, edgecolor='r', fill=False, linewidth=2)
        self.ax.add_patch(self.circ)
        
        # Update display
        self.draw()

print("slice_viewer: module definition complete!")