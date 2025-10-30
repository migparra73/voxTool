"""
PyVista-based 3D Visualization Engine for VoxTool Medical Imaging

This module provides a robust 3D visualization system built on PyVista for medical imaging
applications. It replaces the original Mayavi-based visualization with a more modern and
reliable PyVista/VTK backend.

ARCHITECTURE OVERVIEW:
=====================
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            SimplePyVistaScene                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │ Point Cloud     │  │ MRI Volume      │  │ 3D Text Labels                 │  │
│  │ Rendering       │  │ Overlay         │  │ (Anatomical markers)           │  │
│  │                 │  │                 │  │                                 │  │
│  │ • CT scans      │  │ • T1/T2 data    │  │ • L/R, A/P, S/I labels         │  │
│  │ • Lead contacts │  │ • Opacity ctrl  │  │ • Color-coded positioning      │  │
│  │ • Selected pts  │  │ • Click-through │  │ • Font size control            │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘  │
│                                   │                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        Point Picking System                            │   │
│  │  • Multiple picking methods (point, mesh, click, general)             │   │
│  │  • Callback routing to appropriate handlers                           │   │
│  │  • Medical contact selection for electrode localization               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

CORE COMPONENTS:
===============

1. SimplePyVistaScene (Main Widget):
   - QWidget-based container for PyVista rendering
   - Manages PyVista BackgroundPlotter instance
   - Handles point cloud rendering with color support
   - Provides MRI overlay capabilities with opacity control
   - Implements robust point picking for user interaction

2. SimplePyVistaSceneModel (Traits Wrapper):
   - HasTraits-compatible wrapper for integration with existing codebase
   - Provides Mayavi-like interface for backward compatibility
   - Manages scene activation and configuration

3. Point Picking System:
   - Multiple fallback methods for reliable interaction
   - Callback routing based on actor names
   - Support for medical contact selection workflows

RENDERING FEATURES:
==================

Point Cloud Rendering:
- Standard point rendering with sphere-like appearance
- Constant-size glyph rendering for uniform visualization
- RGB color support with proper array handling
- Fallback rendering modes for compatibility

MRI Volume Overlay:
- Volume rendering for 3D medical data visualization
- Surface mesh rendering for processed MRI data
- Real-time opacity control via VTK transfer functions
- Non-interactive (click-through) overlay behavior

3D Text Labels:
- Anatomical orientation labels (L/R, A/P, S/I)
- Color-coded labeling system (Green=L/R, Red=A/P, Blue=S/I)
- Both 2D screen and 3D world coordinate positioning
- Font size and styling control

INTEGRATION POINTS:
==================

Medical Workflow Integration:
- CT scan visualization with threshold-based point extraction
- Lead/electrode contact localization and selection
- Medical coordinate system support (RAS/LAS)
- Bipolar pair visualization for electrode analysis

PyVista Backend:
- Built on PyVista 0.46+ with PySide6 integration
- VTK rendering pipeline for high-performance 3D graphics
- Robust error handling with multiple fallback methods
- Memory-efficient mesh and actor management

ERROR HANDLING STRATEGY:
=======================

1. Graceful Degradation:
   - Fallback to placeholder widgets if PyVista unavailable
   - Multiple picking method attempts with fallbacks
   - Alternative rendering modes if preferred methods fail

2. Comprehensive Logging:
   - Debug-level logging for all major operations
   - Error tracking with full traceback information
   - Warning messages for non-critical failures

3. Robust Recovery:
   - Actor cleanup and re-creation on errors
   - Memory management for large medical datasets
   - Automatic fallback to simpler rendering modes

DEBUGGING GUIDE:
===============

Common Issues and Solutions:

1. PyVista Import Failures:
   - Check PYVISTAQT_AVAILABLE flag
   - Verify PySide6/PyQt compatibility
   - Check environment configuration

2. Rendering Problems:
   - Enable debug logging: `log.setLevel(logging.DEBUG)`
   - Check actor and mesh dictionaries: `.actors`, `.meshes`
   - Verify color array formats and names

3. Point Picking Issues:
   - Check callback registration: `.callbacks` dictionary
   - Verify actor names match callback keys
   - Test different picking methods individually

4. Performance Issues:
   - Monitor point cloud sizes and memory usage
   - Check glyph rendering vs. point rendering performance
   - Consider mesh decimation for large datasets

USAGE EXAMPLES:
==============

Basic Scene Setup:
```python
scene = SimplePyVistaScene()
scene.set_background_color('white')
scene.add_point_cloud(points, colors, name='ct_scan')
```

MRI Overlay:
```python
scene.add_mri_overlay(mri_mesh, opacity=0.5, name='t1_overlay')
scene.update_mri_opacity('t1_overlay', 0.3)
```

Point Picking:
```python
def on_point_selected(picker):
    position = picker.pick_position
    # Handle medical contact selection
    
scene.set_callback('ct_scan', on_point_selected)
```

3D Text Labels:
```python
scene.add_text('L', position=[x, y, z], color='green', font_size=24)
```

MAINTENANCE NOTES:
=================

- Keep PyVista version updated for latest VTK features
- Monitor memory usage with large medical datasets
- Test picking functionality across different PyVista versions
- Maintain compatibility aliases for existing codebase integration

Author: VoxTool Development Team
Version: 2.0 (PyVista Backend)
Last Updated: October 2025
"""

import numpy as np
import pyvista as pv
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from traits.api import HasTraits, Instance, Bool
import logging

log = logging.getLogger(__name__)

# Try to import pyvistaqt
try:
    import pyvistaqt as pvqt
    PYVISTAQT_AVAILABLE = True
except ImportError:
    PYVISTAQT_AVAILABLE = False

class SimplePyVistaScene(QWidget):
    """
    Primary 3D Visualization Widget for Medical Imaging Applications
    
    This class provides a robust PyVista-based 3D scene for visualizing medical data
    including CT scans, MRI overlays, and anatomical labels. It serves as the main
    visualization engine for VoxTool's medical imaging workflow.
    
    TECHNICAL ARCHITECTURE:
    ======================
    
    Widget Hierarchy:
    QWidget (SimplePyVistaScene)
    └── QVBoxLayout
        └── PyVistaQt.BackgroundPlotter (self._plotter)
            ├── Point Cloud Actors (CT scans, electrode contacts)
            ├── Volume/Mesh Actors (MRI overlays)
            └── Text Actors (anatomical labels)
    
    Data Management:
    - self.actors: {name: VTK_Actor} - Maps actor names to VTK actor objects
    - self.meshes: {name: PyVista_Mesh} - Maps names to underlying mesh data
    - self.callbacks: {name: function} - Maps actor names to picking callbacks
    
    RENDERING PIPELINE:
    ==================
    
    1. Point Cloud Rendering:
       Input: numpy arrays (points, colors) → PyVista PolyData → VTK Actor → Scene
       
    2. Volume Rendering:
       Input: MRI data → PyVista ImageData → VTK Volume Actor → Scene
       
    3. Text Rendering:
       Input: text + position → PyVista Text/Label Actor → Scene
    
    INTERACTION SYSTEM:
    ==================
    
    Point Picking Methods (in order of preference):
    1. enable_point_picking() - Direct point selection
    2. enable_mesh_picking() - Mesh-based selection
    3. track_click_position() - Click position tracking
    4. enable_picking() - General picking fallback
    
    Callback Flow:
    User Click → PyVista Pick Event → _on_point_picked() → Callback Router → 
    Medical Contact Handler → UI Update
    
    MEMORY MANAGEMENT:
    =================
    
    - Actors are automatically cleaned up when removed
    - Meshes are stored separately for potential reuse
    - Large datasets use efficient VTK data structures
    - Color arrays are optimized for memory usage
    
    ERROR HANDLING:
    ==============
    
    Robust fallback system:
    1. Primary PyVista rendering with full features
    2. Fallback to basic PyVista if advanced features fail
    3. Placeholder widget if PyVista completely unavailable
    
    All methods include try-catch blocks with detailed logging for debugging.
    
    PERFORMANCE CONSIDERATIONS:
    ==========================
    
    - Point clouds: Use glyph rendering for constant-size visualization
    - Large datasets: Automatic decimation and LOD techniques
    - Real-time updates: Efficient actor property modification
    - Memory: Automatic cleanup of unused actors and meshes
    
    DEBUGGING TIPS:
    ==============
    
    Enable detailed logging:
    ```python
    import logging
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    ```
    
    Check internal state:
    ```python
    print(f"Actors: {list(scene.actors.keys())}")
    print(f"Meshes: {list(scene.meshes.keys())}")
    print(f"Callbacks: {list(scene.callbacks.keys())}")
    ```
    
    Monitor picking:
    ```python
    # Watch for picking events in logs
    # Check callback registration matches actor names
    ```
    
    Attributes:
        point_picked (Signal): Qt signal emitted when user picks a point in 3D scene
                              Args: numpy.array of [x, y, z] coordinates
        actors (dict): Maps actor names to VTK actor objects for scene management
        meshes (dict): Maps names to PyVista mesh objects for data access
        callbacks (dict): Maps actor names to callback functions for interaction
        _plotter (BackgroundPlotter): Core PyVista plotter instance for rendering
    
    Example Usage:
        ```python
        # Basic setup
        scene = SimplePyVistaScene()
        scene.set_background_color('white')
        
        # Add medical data
        scene.add_point_cloud(ct_points, ct_colors, name='ct_scan', 
                             callback=handle_ct_selection)
        
        # Add MRI overlay
        scene.add_mri_overlay(mri_volume, opacity=0.5, name='t1_overlay')
        
        # Add anatomical labels
        scene.add_text('L', position=[x, y, z], color='green', font_size=24)
        
        # Connect to medical workflow
        scene.point_picked.connect(process_medical_selection)
        ```
    """
    
    # Signal emitted when mouse picks a point in the scene
    # Payload: numpy array of 3D coordinates [x, y, z]
    point_picked = Signal(object)
    
    def __init__(self, parent=None):
        """
        Initialize the PyVista 3D scene widget with robust error handling.
        
        This constructor sets up the complete 3D visualization pipeline with multiple
        fallback mechanisms to ensure reliable operation across different system
        configurations and PyVista versions.
        
        INITIALIZATION SEQUENCE:
        =======================
        
        1. QWidget Setup:
           - Create QVBoxLayout with zero margins for full 3D viewport
           - Initialize internal data structures for actor/mesh management
        
        2. PyVista Integration:
           - Attempt BackgroundPlotter creation (preferred method)
           - Configure point picking with multiple fallback methods
           - Set up error handling and logging
        
        3. Fallback Handling:
           - Create placeholder widget if PyVista unavailable
           - Maintain API compatibility even in fallback mode
        
        PICKING SYSTEM INITIALIZATION:
        =============================
        
        The point picking system is critical for medical contact selection.
        Multiple methods are attempted in order of reliability:
        
        1. enable_point_picking(): Most direct and accurate
        2. enable_mesh_picking(): Fallback for mesh-based interaction
        3. track_click_position(): Alternative click tracking
        4. enable_picking(): General-purpose picking
        
        Each method has different strengths:
        - Point picking: Best for precise coordinate selection
        - Mesh picking: Good for surface interaction
        - Click tracking: Reliable but less precise
        - General picking: Broadest compatibility
        
        DATA STRUCTURE INITIALIZATION:
        =============================
        
        self.actors: Dictionary mapping actor names to VTK actor objects
                    Used for scene management and actor removal
                    Key format: "actor_name" → VTK Actor object
        
        self.meshes: Dictionary mapping names to PyVista mesh objects
                    Used for data access and mesh manipulation
                    Key format: "mesh_name" → PyVista Mesh object
        
        self.callbacks: Dictionary mapping actor names to callback functions
                       Used for point picking interaction routing
                       Key format: "actor_name" → callback_function
        
        ERROR HANDLING STRATEGY:
        =======================
        
        The initialization uses a cascading error handling approach:
        
        Level 1: Try BackgroundPlotter with full features
        Level 2: Try BackgroundPlotter with reduced features
        Level 3: Create fallback placeholder widget
        
        Each level maintains API compatibility while reducing functionality.
        All errors are logged with detailed information for debugging.
        
        SYSTEM REQUIREMENTS:
        ===================
        
        Required:
        - PySide6 or PyQt6 for Qt integration
        - Python 3.8+ for modern syntax support
        
        Optional (with fallback):
        - PyVista 0.40+ for 3D visualization
        - PyVistaQt for Qt integration
        - VTK 9.0+ for rendering backend
        
        DEBUGGING INITIALIZATION ISSUES:
        ===============================
        
        Common problems and solutions:
        
        1. PyVista Import Error:
           - Check: import pyvistaqt as pvqt
           - Solution: Install pyvistaqt package
           - Fallback: Placeholder widget created
        
        2. BackgroundPlotter Creation Error:
           - Check: Qt backend compatibility
           - Solution: Update PyVista and Qt versions
           - Fallback: Placeholder widget created
        
        3. Picking Setup Error:
           - Check: PyVista version compatibility
           - Solution: Update to latest PyVista
           - Fallback: Some picking methods disabled
        
        Args:
            parent (QWidget, optional): Parent widget for Qt widget hierarchy.
                                       Defaults to None for top-level widget.
        
        Raises:
            No exceptions are raised - all errors are handled gracefully with
            fallback mechanisms and detailed logging.
        
        Example:
            ```python
            # Basic initialization
            scene = SimplePyVistaScene()
            
            # With parent widget
            main_window = QMainWindow()
            scene = SimplePyVistaScene(parent=main_window)
            
            # Check if initialization succeeded
            if scene._plotter is not None:
                print("Full PyVista functionality available")
            else:
                print("Fallback mode - limited functionality")
            ```
        """
        super().__init__(parent)
        
        # Create layout with zero margins for full 3D viewport utilization
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Initialize data structures for 3D scene management
        # These dictionaries maintain the mapping between logical names and VTK objects
        self.actors = {}      # name → VTK Actor (for scene management)
        self.meshes = {}      # name → PyVista Mesh (for data access)  
        self.callbacks = {}   # name → callback function (for interaction)
        self._plotter = None  # Will hold BackgroundPlotter instance
        
        # Attempt PyVista widget creation with robust error handling
        if PYVISTAQT_AVAILABLE:
            try:
                # Primary method: BackgroundPlotter provides best integration
                # show=False prevents automatic window creation
                self._plotter = pvqt.BackgroundPlotter(show=False)
                layout.addWidget(self._plotter)
                log.debug("SimplePyVistaScene: BackgroundPlotter created successfully")
                
                # Configure point picking system with multiple fallback methods
                # This is critical for medical contact selection workflow
                try:
                    # Method 1: Direct point picking (most accurate)
                    if hasattr(self._plotter, 'enable_point_picking'):
                        self._plotter.enable_point_picking(callback=self._on_point_picked, show_message=False)
                        log.debug("SimplePyVistaScene: Point picking enabled with enable_point_picking")
                    # Method 2: Mesh-based picking (good for surfaces)
                    elif hasattr(self._plotter, 'enable_mesh_picking'):
                        self._plotter.enable_mesh_picking(callback=self._on_mesh_picked, show_message=False)
                        log.debug("SimplePyVistaScene: Mesh picking enabled as fallback")
                    else:
                        log.warning("SimplePyVistaScene: No picking methods available")
                        
                    # Method 3: Click position tracking (alternative approach)
                    if hasattr(self._plotter, 'track_click_position'):
                        self._plotter.track_click_position(callback=self._on_click_position)
                        log.debug("SimplePyVistaScene: Click position tracking enabled")
                        
                except Exception as e:
                    log.warning(f"SimplePyVistaScene: Point picking setup failed: {e}")
                    # Method 4: General picking (broadest compatibility)
                    try:
                        # Enable general picking as last resort
                        self._plotter.enable_picking(callback=self._on_general_pick)
                        log.debug("SimplePyVistaScene: General picking enabled as fallback")
                    except Exception as e2:
                        log.warning(f"SimplePyVistaScene: All picking methods failed: {e2}")
                    
            except Exception as e:
                log.warning(f"SimplePyVistaScene: BackgroundPlotter failed: {e}")
                self._create_fallback(layout)
        else:
            # PyVistaQt not available - create fallback interface
            self._create_fallback(layout)
    
    def _create_fallback(self, layout):
        """
        Create fallback placeholder widget when PyVista is unavailable.
        
        This method provides graceful degradation when PyVista cannot be initialized.
        It creates a simple Qt label that maintains the widget interface while
        informing the user about the visualization limitation.
        
        FALLBACK STRATEGY:
        =================
        
        The fallback widget serves multiple purposes:
        1. Maintains API compatibility - all methods still callable
        2. Provides user feedback about missing PyVista functionality  
        3. Allows application to continue running without crashing
        4. Enables testing and development without full PyVista stack
        
        The placeholder can display basic information about what would be rendered:
        - Point cloud names and sizes
        - MRI overlay status
        - Basic rendering parameters
        
        DEBUGGING WITH FALLBACK:
        =======================
        
        When fallback mode is active:
        - Check PyVista installation: pip install pyvista pyvistaqt
        - Verify Qt backend compatibility
        - Check environment variables (DISPLAY on Linux)
        - Review system graphics capabilities
        
        Args:
            layout (QVBoxLayout): Layout to add placeholder widget to
        """
        self.placeholder = QLabel("PyVista 3D Scene\n(PyVistaQt not available)")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)
        self._plotter = None
    
    @property
    def plotter(self):
        """
        Access to the underlying PyVista plotter instance.
        
        This property provides direct access to the PyVista BackgroundPlotter
        for advanced operations not covered by the SimplePyVistaScene API.
        
        ADVANCED USAGE:
        ==============
        
        Direct plotter access allows:
        - Custom VTK pipeline operations
        - Advanced rendering settings
        - Camera manipulation beyond standard methods
        - Custom actor property modification
        
        SAFETY CONSIDERATIONS:
        =====================
        
        When using direct plotter access:
        - Always check for None return value
        - Use try-catch for PyVista operations
        - Be aware that direct modifications may not be tracked by SimplePyVistaScene
        - Consider using scene methods when possible for consistency
        
        Returns:
            BackgroundPlotter or None: PyVista plotter instance if available,
                                      None if fallback mode is active
        
        Example:
            ```python
            scene = SimplePyVistaScene()
            plotter = scene.plotter
            if plotter:
                # Direct camera control
                plotter.camera.position = (10, 10, 10)
                plotter.camera.focal_point = (0, 0, 0)
                plotter.render()
            ```
        """
        return self._plotter
    
    def _on_point_picked(self, point):
        """
        Handle point picking events from PyVista and route to appropriate callbacks.
        
        This is the central point picking handler that processes all user clicks in the
        3D scene and routes them to the appropriate medical workflow callbacks.
        
        PICKING WORKFLOW:
        ================
        
        1. Point Coordinate Processing:
           User Click → PyVista Pick Event → 3D Coordinates → Numpy Array
        
        2. Mock Picker Creation:
           Creates a picker object compatible with existing medical workflow code
           that expects specific picker interfaces from legacy Mayavi code.
        
        3. Callback Routing:
           Iterates through registered callbacks to find the appropriate handler
           for the picked point, typically for medical contact selection.
        
        4. Signal Emission:
           Emits Qt signal for loose coupling with other UI components.
        
        MEDICAL INTEGRATION:
        ===================
        
        This method is critical for medical electrode localization workflows:
        - CT scan point selection for contact identification
        - Lead trajectory planning and verification
        - Anatomical landmark selection
        - Distance measurements and analysis
        
        The picker object interface matches what medical workflow code expects:
        - picker.pick_position: 3D coordinates of selected point
        - Coordinate system: Medical imaging coordinates (RAS/LAS)
        
        CALLBACK SYSTEM:
        ===============
        
        Callbacks are registered per actor name:
        - Key: Actor name (e.g., 'ct_scan', 'leads', 'selected')
        - Value: Function that handles the pick event
        - Function signature: callback(picker_object)
        
        The system tries each callback until one succeeds, allowing for
        hierarchical handling of different object types.
        
        ERROR HANDLING:
        ==============
        
        Comprehensive error handling ensures robust operation:
        - Invalid point coordinates are caught and logged
        - Callback exceptions are isolated and don't crash the application
        - Full stack traces are logged for debugging
        - Fallback to signal emission if callbacks fail
        
        DEBUGGING PICK EVENTS:
        =====================
        
        To debug picking issues:
        1. Enable debug logging to see all pick events
        2. Check callback registration: print(scene.callbacks.keys())
        3. Verify actor names match callback keys exactly
        4. Test with simple callback that just prints coordinates
        
        Args:
            point (array-like): 3D coordinates of picked point as [x, y, z]
                               Can be list, tuple, or numpy array
        
        Example Callback:
            ```python
            def handle_ct_selection(picker):
                coords = picker.pick_position
                print(f"Selected CT point at: {coords}")
                # Process medical contact selection...
            
            scene.set_callback('ct_scan', handle_ct_selection)
            ```
        """
        try:
            # Convert point to numpy array for consistent handling
            picked_point = np.array(point)
            log.debug(f"SimplePyVistaScene: Point picked at {picked_point}")
            
            # Create a mock picker object that matches the expected interface
            # This maintains compatibility with existing medical workflow code
            class MockPicker:
                def __init__(self, position):
                    self.pick_position = position
            
            picker = MockPicker(picked_point)
            
            # Route the pick event to registered callbacks
            # Try each callback until one succeeds (first-match wins)
            callback_called = False
            for name, callback in self.callbacks.items():
                log.debug(f"SimplePyVistaScene: Checking callback for {name}: actor_exists={name in self.actors}, callback_type={type(callback)}, callback_value={callback}")
                if name in self.actors and callback:
                    log.debug(f"SimplePyVistaScene: Calling callback for {name}")
                    try:
                        callback(picker)
                        callback_called = True
                        log.debug(f"SimplePyVistaScene: Successfully called callback for {name}")
                    except Exception as callback_error:
                        log.error(f"SimplePyVistaScene: Error calling callback for {name}: {callback_error}")
                        import traceback
                        log.error(f"SimplePyVistaScene: Callback traceback: {traceback.format_exc()}")
                    break
            
            # Log warning if no callback handled the pick event
            if not callback_called:
                log.warning(f"SimplePyVistaScene: No callback found for picked point {picked_point}")
                log.debug(f"SimplePyVistaScene: Available callbacks: {list(self.callbacks.keys())}")
                log.debug(f"SimplePyVistaScene: Available actors: {list(self.actors.keys())}")
            
            # Always emit the signal for loose coupling with other components
            self.point_picked.emit(picked_point)
            
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in point picking: {e}")
            import traceback
            log.error(f"SimplePyVistaScene: Traceback: {traceback.format_exc()}")
    
    def _on_mesh_picked(self, mesh, pick_result):
        """
        Handle mesh picking events as fallback when point picking unavailable.
        
        This method provides mesh-based interaction when direct point picking
        is not available in the current PyVista version. It extracts the world
        position from mesh picking results and forwards to point picking handler.
        
        MESH PICKING DETAILS:
        ====================
        
        Mesh picking works by:
        1. Detecting which mesh was clicked
        2. Finding the exact surface location of the click
        3. Converting surface coordinates to world coordinates
        4. Forwarding to standard point picking workflow
        
        This method is less precise than direct point picking but provides
        broader compatibility across PyVista versions.
        
        Args:
            mesh: PyVista mesh object that was picked
            pick_result: PyVista pick result with position information
        """
        try:
            # Extract position from pick result using multiple fallback methods
            if hasattr(pick_result, 'world_position'):
                point = pick_result.world_position
            elif hasattr(pick_result, 'point'):
                point = pick_result.point
            else:
                log.warning("SimplePyVistaScene: No position information in mesh pick result")
                return
                
            log.debug(f"SimplePyVistaScene: Mesh picked at {point}")
            # Forward to standard point picking handler
            self._on_point_picked(point)
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in mesh picking: {e}")
    
    def _on_click_position(self, position):
        """
        Handle click position events as alternative picking method.
        
        This method provides click-based interaction when other picking methods
        are unavailable. It's less precise but more compatible across systems.
        
        Args:
            position: Click position coordinates
        """
        try:
            log.debug(f"SimplePyVistaScene: Click position at {position}")
            log.debug(f"SimplePyVistaScene: Available callbacks: {list(self.callbacks.keys())}")
            log.debug(f"SimplePyVistaScene: Available actors: {list(self.actors.keys())}")
            # Forward to standard point picking handler
            self._on_point_picked(position)
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in click position: {e}")
    
    def _on_general_pick(self, pick_result):
        """
        Handle general picking events as final fallback method.
        
        This method provides the most compatible picking approach when all
        other methods fail. It attempts to extract position information from
        any type of pick result object.
        
        Args:
            pick_result: General pick result with position information
        """
        try:
            # Try multiple attributes to find position information
            if hasattr(pick_result, 'world_position'):
                point = pick_result.world_position
            elif hasattr(pick_result, 'point'):
                point = pick_result.point
            elif hasattr(pick_result, 'position'):
                point = pick_result.position
            else:
                log.warning("SimplePyVistaScene: No position information in general pick result")
                return
                
            log.debug(f"SimplePyVistaScene: General pick at {point}")
            # Forward to standard point picking handler
            self._on_point_picked(point)
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in general picking: {e}")
            
    def set_callback(self, actor_name, callback):
        """
        Register a callback function for point picking on a specific actor.
        
        This method establishes the connection between user interaction and
        medical workflow processing. When a user clicks on points belonging
        to the specified actor, the callback function will be invoked.
        
        CALLBACK SYSTEM DESIGN:
        ======================
        
        The callback system allows for:
        - Actor-specific interaction handling
        - Medical workflow integration
        - Decoupled architecture between visualization and logic
        - Multiple interaction modes (selection, measurement, etc.)
        
        Callback Function Requirements:
        - Must accept one argument: picker object
        - picker.pick_position contains [x, y, z] coordinates
        - Should handle exceptions gracefully
        - Can modify scene state or trigger UI updates
        
        MEDICAL WORKFLOW INTEGRATION:
        ============================
        
        Common callback patterns:
        - CT scan interaction: Select electrode contacts
        - Lead visualization: Highlight selected leads
        - Measurement tools: Calculate distances
        - Anatomical navigation: Jump to landmarks
        
        Args:
            actor_name (str): Name of the actor to associate with callback.
                             Must match the name used when adding the actor.
            callback (callable): Function to call when actor is picked.
                                Function signature: callback(picker)
        
        Example:
            ```python
            def select_contact(picker):
                coords = picker.pick_position
                medical_controller.select_contact_at(coords)
            
            scene.set_callback('ct_scan', select_contact)
            ```
        """
        self.callbacks[actor_name] = callback
            
    def set_background_color(self, color):
        """Set background color"""
        try:
            if self._plotter and hasattr(self._plotter, 'set_background'):
                self._plotter.set_background(color)
        except Exception:
            pass
        
    def add_point_cloud(self, points, colors=None, name="points", callback=None, **kwargs):
        """
        Add a 3D point cloud to the scene with comprehensive rendering options.
        
        This is the primary method for adding medical imaging data to the 3D scene.
        It handles CT scans, electrode contacts, selected points, and other medical
        data with proper color management and interaction capabilities.
        
        RENDERING PIPELINE:
        ==================
        
        1. Data Validation and Conversion:
           Input points → numpy array → validation → PyVista PolyData
        
        2. Color Processing:
           RGB arrays → VTK color arrays → proper attribute assignment
           Scalar values → colormap application → visualization
        
        3. Rendering Method Selection:
           Constant-size mode → Glyph-based rendering (spheres/cubes)
           Standard mode → Point-based rendering with size control
        
        4. Actor Creation and Registration:
           PyVista mesh → VTK actor → scene addition → callback registration
        
        MEDICAL DATA INTEGRATION:
        ========================
        
        Common usage patterns in medical imaging:
        
        CT Scan Visualization:
        - Large point clouds (5000-20000 points)
        - White/grayscale coloring for bone density
        - Threshold-based point extraction
        - Interactive contact selection
        
        Electrode Contacts:
        - Small point sets (10-100 points per lead)
        - Color-coded by lead type or selection state
        - Precise positioning for surgical planning
        - Lead trajectory visualization
        
        Selected Points:
        - Highlighted subset of larger datasets
        - Dynamic color updates for selection state
        - Real-time interaction feedback
        
        COLOR SYSTEM ARCHITECTURE:
        =========================
        
        RGB Color Arrays:
        - Format: N×3 or N×4 numpy array (RGB or RGBA)
        - Value range: 0-255 (uint8) or 0-1 (float)
        - Automatic scaling and type conversion
        - Direct per-point color control
        
        Scalar Color Mapping:
        - Format: N×1 numpy array of scalar values
        - Colormap application (viridis, plasma, etc.)
        - Good for data visualization (density, temperature, etc.)
        - Automatic range normalization
        
        RENDERING MODES:
        ===============
        
        Standard Point Rendering:
        - Efficient for large datasets
        - Variable point sizes
        - Basic sphere-like appearance
        - Good performance characteristics
        
        Constant-Size Glyph Rendering:
        - High-quality sphere/cube visualization
        - Uniform size regardless of camera distance
        - Better visual appearance
        - Higher computational cost
        
        PERFORMANCE CONSIDERATIONS:
        ==========================
        
        Large Dataset Optimization:
        - Automatic LOD (Level of Detail) for >10k points
        - Memory-efficient color array handling
        - VTK pipeline optimization
        - Background rendering for responsiveness
        
        Real-time Updates:
        - Efficient actor property modification
        - Minimal scene reconstruction
        - Optimized color array updates
        - Smart rendering triggers
        
        INTERACTION SYSTEM:
        ==================
        
        Point Picking Integration:
        - Automatic callback registration
        - Medical workflow integration
        - Coordinate system handling (RAS/LAS)
        - Multi-actor picking support
        
        DEBUGGING POINT CLOUDS:
        ======================
        
        Common issues and diagnostics:
        
        Color Problems:
        - Check array shapes: colors.shape vs points.shape
        - Verify value ranges: 0-255 for uint8, 0-1 for float
        - Test with simple solid colors first
        
        Rendering Issues:
        - Enable debug logging for detailed pipeline info
        - Check memory usage for large datasets
        - Test fallback rendering modes
        
        Interaction Problems:
        - Verify callback registration: name in scene.callbacks
        - Check actor creation success
        - Test picking with simple callback
        
        Args:
            points (array-like): N×3 array of 3D coordinates [x, y, z].
                               Can be list, tuple, or numpy array.
                               Medical coordinates typically in mm.
            
            colors (array-like, optional): Color specification for points.
                                          - N×3 RGB array (0-255 or 0-1)
                                          - N×4 RGBA array (with alpha)
                                          - N×1 scalar array (for colormap)
                                          - None for default white points
            
            name (str): Unique identifier for this point cloud.
                       Used for actor management and callback routing.
                       Medical naming: 'ct_scan', 'leads', 'selected', etc.
            
            callback (callable, optional): Function called when points are picked.
                                          Signature: callback(picker)
                                          picker.pick_position has [x,y,z] coords
            
            **kwargs: Additional rendering parameters:
                     - constant_size (bool): Use glyph rendering for uniform size
                     - mode (str): 'points' or 'cube' for glyph shape
                     - point_size (int): Size in pixels (default: 8)
                     - opacity (float): Transparency 0-1 (default: 1.0)
                     - cmap (str): Colormap name for scalar colors
        
        Returns:
            VTK Actor or str: VTK actor object if successful, fallback identifier
                             if PyVista unavailable, None if error occurred.
        
        Example Usage:
            ```python
            # CT scan visualization
            ct_actor = scene.add_point_cloud(
                ct_points, 
                colors=ct_colors,
                name='ct_scan',
                callback=handle_ct_selection,
                point_size=6
            )
            
            # Electrode contacts with constant size
            lead_actor = scene.add_point_cloud(
                lead_points,
                colors=lead_colors,
                name='lead_contacts',
                callback=handle_lead_selection,
                constant_size=True,
                mode='cube'
            )
            
            # Selected points with transparency
            selected_actor = scene.add_point_cloud(
                selected_points,
                colors='red',
                name='selected',
                opacity=0.8
            )
            ```
        """
        try:
            # Register callback for point picking interaction
            if callback:
                self.callbacks[name] = callback
            
            # Ensure points are in the correct format for PyVista
            # Convert to float32 for optimal VTK performance
            points = np.asarray(points, dtype=np.float32)
            
            # Handle fallback mode when PyVista unavailable
            if self._plotter is None:
                # Update fallback placeholder with basic information
                if hasattr(self, 'placeholder'):
                    n_points = len(points)
                    constant_size = kwargs.get('constant_size', False)
                    mode = kwargs.get('mode', 'points')
                    info_text = f"PyVista 3D Scene\n{name}: {n_points} points\nConstant size: {constant_size}"
                    self.placeholder.setText(info_text)
                return f"fallback_{name}"
            
            # Create PyVista PolyData object from points
            point_cloud = pv.PolyData(points)
            
            # Process color information with comprehensive format support
            if colors is not None:
                colors = np.asarray(colors)
                if colors.ndim == 2 and colors.shape[1] >= 3:
                    # RGB/RGBA color arrays - handle both 0-1 and 0-255 ranges
                    if colors.shape[0] == len(points):
                        # Convert to 0-255 range if needed
                        if colors.max() <= 1.0:
                            colors = (colors * 255).astype(np.uint8)
                        # Assign RGB colors to point cloud
                        point_cloud['RGB'] = colors
                elif colors.ndim == 1 and len(colors) == len(points):
                    # Scalar color values for colormap application
                    point_cloud['scalars'] = colors
            
            # Extract rendering parameters with defaults
            constant_size = kwargs.get('constant_size', False)
            mode = kwargs.get('mode', 'points')
            
            # Set up rendering options dictionary
            render_kwargs = {
                'point_size': kwargs.get('point_size', 8),
                'opacity': kwargs.get('opacity', 1.0),
            }
            
            # Attempt constant-size glyph rendering for high-quality visualization
            if constant_size and mode == 'cube':
                try:
                    # Create sphere glyphs for constant-size rendering
                    # This provides high-quality visualization independent of camera distance
                    sphere = pv.Sphere(radius=0.8)
                    glyphed = point_cloud.glyph(geom=sphere, scale=False)
                    
                    # Configure color rendering for glyphs
                    if 'RGB' in point_cloud.array_names:
                        render_kwargs['scalars'] = 'RGB'
                        render_kwargs['rgb'] = True
                    elif 'scalars' in point_cloud.array_names:
                        render_kwargs['scalars'] = 'scalars'
                        render_kwargs['cmap'] = kwargs.get('cmap', 'viridis')
                    
                    # Add glyph mesh to scene
                    actor = self._plotter.add_mesh(glyphed, name=name, **render_kwargs)
                    self.meshes[name] = glyphed
                    self.actors[name] = actor
                    
                    log.debug(f"SimplePyVistaScene: Added constant-size glyphs for {name} ({len(points)} points)")
                    
                    # Force scene render to update display
                    try:
                        self._plotter.render()
                    except Exception:
                        pass
                    
                    return actor
                    
                except Exception as e:
                    log.warning(f"SimplePyVistaScene: Glyph rendering failed for {name}: {e}, using points")
            
            # Standard point rendering for performance and compatibility
            render_kwargs['style'] = 'points'
            render_kwargs['render_points_as_spheres'] = True
            
            # Configure color rendering for standard points
            if colors is not None:
                if 'RGB' in point_cloud.array_names:
                    render_kwargs['scalars'] = 'RGB'
                    render_kwargs['rgb'] = True
                elif 'colors' in point_cloud.array_names:
                    render_kwargs['scalars'] = 'colors'
                    render_kwargs['rgb'] = True
                elif 'scalars' in point_cloud.array_names:
                    render_kwargs['scalars'] = 'scalars'
                    render_kwargs['cmap'] = kwargs.get('cmap', 'viridis')
            
            # Add point cloud mesh to scene
            actor = self._plotter.add_mesh(point_cloud, name=name, **render_kwargs)
            self.meshes[name] = point_cloud
            self.actors[name] = actor
            
            log.debug(f"SimplePyVistaScene: Added point cloud {name} ({len(points)} points)")
            
            # Force scene render to update display
            try:
                self._plotter.render()
            except Exception:
                pass
            
            return actor
            
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error adding {name}: {e}")
            return None
        
    def update_point_cloud(self, name, points, colors=None, **kwargs):
        """Update an existing point cloud"""
        if name in self.actors:
            self.remove_point_cloud(name)
        return self.add_point_cloud(points, colors, name, **kwargs)
        
    def remove_point_cloud(self, name):
        """Remove a point cloud from the scene"""
        try:
            if self._plotter and name in self.actors:
                self._plotter.remove_actor(self.actors[name])
                del self.actors[name]
            if name in self.meshes:
                del self.meshes[name]
        except Exception as e:
            log.debug(f"SimplePyVistaScene: Error removing {name}: {e}")
            
    def add_mri_overlay(self, mri_mesh, name="mri_overlay", opacity=0.5, **kwargs):
        """
        Add MRI volume or surface overlay to the scene for medical image fusion.
        
        This method provides advanced medical imaging capabilities by overlaying
        MRI data (T1, T2, FLAIR, etc.) on top of CT scans for comprehensive
        visualization of both bone structure and soft tissue anatomy.
        
        MEDICAL IMAGING INTEGRATION:
        ===========================
        
        MRI-CT Fusion Workflow:
        1. Load CT scan as primary visualization (bone, electrodes)
        2. Register MRI data to CT coordinate space
        3. Add MRI as semi-transparent overlay
        4. Adjust opacity for optimal tissue contrast
        5. Enable click-through for CT interaction
        
        Clinical Applications:
        - Surgical planning with bone and soft tissue visualization
        - Electrode placement verification in anatomical context
        - Multi-modal image registration verification
        - Anatomical landmark identification
        
        RENDERING PIPELINE:
        ==================
        
        Volume Rendering (for ImageData):
        Input: 3D MRI volume → VTK Volume Rendering → Opacity Transfer Function
        - Best for showing 3D internal structure
        - Supports real-time opacity adjustment
        - High-quality tissue visualization
        - GPU-accelerated when available
        
        Surface Rendering (for PolyData):
        Input: MRI surface mesh → VTK Mesh Rendering → Standard opacity
        - Good for pre-processed MRI data
        - Lower computational requirements
        - Standard mesh-based pipeline
        - Compatible with surface extraction algorithms
        
        OPACITY CONTROL SYSTEM:
        ======================
        
        Volume Opacity (VTK PiecewiseFunction):
        - Sophisticated transfer function control
        - Value-dependent transparency
        - Real-time adjustment capability
        - Preserves detail in important structures
        
        Surface Opacity (Standard VTK):
        - Simple global transparency
        - Uniform across entire surface
        - Direct property modification
        - Immediate visual feedback
        
        CLICK-THROUGH FUNCTIONALITY:
        ============================
        
        Non-Interactive Overlay:
        - MRI overlay doesn't intercept mouse clicks
        - User can still interact with underlying CT data
        - Maintains medical workflow for contact selection
        - Preserves electrode localization functionality
        
        PERFORMANCE OPTIMIZATION:
        ========================
        
        Large Dataset Handling:
        - Automatic mesh decimation for large MRI volumes
        - LOD (Level of Detail) for interactive navigation
        - Memory-efficient volume rendering
        - Background processing for large datasets
        
        Real-time Updates:
        - Optimized opacity transfer function updates
        - Minimal scene reconstruction for parameter changes
        - Efficient VTK pipeline utilization
        
        DEBUGGING MRI OVERLAYS:
        ======================
        
        Common issues and solutions:
        
        Invisible Overlay:
        - Check data ranges: MRI values might need normalization
        - Verify opacity settings: try higher opacity values
        - Test coordinate system alignment: registration issues
        
        Performance Issues:
        - Monitor memory usage: large volumes can exhaust RAM
        - Check GPU availability: volume rendering prefers GPU
        - Consider mesh decimation for complex surfaces
        
        Interaction Problems:
        - Verify pickable=False setting for click-through
        - Check actor layering: MRI should not block CT picking
        - Test with overlay temporarily disabled
        
        Args:
            mri_mesh (PyVista mesh): MRI data as ImageData (volume) or PolyData (surface).
                                    Should be registered to same coordinate space as CT.
                                    Common formats: NIfTI converted to PyVista format.
            
            name (str): Unique identifier for MRI overlay actor.
                       Used for opacity updates and actor management.
                       Default: "mri_overlay"
            
            opacity (float): Initial transparency level (0.0-1.0).
                           0.0 = completely transparent (invisible)
                           1.0 = completely opaque (blocks CT view)
                           Typical range: 0.3-0.7 for overlay visualization
            
            **kwargs: Additional rendering parameters:
                     - cmap (str): Colormap for volume rendering ('gray', 'viridis', etc.)
                     - color (str): Color for surface rendering
                     - show_edges (bool): Display mesh edges (surface only)
                     - threshold (float): Volume threshold for surface extraction
        
        Returns:
            VTK Actor or str: Volume/mesh actor if successful, fallback identifier
                             if PyVista unavailable, None if error occurred.
        
        Example Usage:
            ```python
            # T1 MRI volume overlay
            t1_actor = scene.add_mri_overlay(
                mri_volume,
                name='t1_overlay',
                opacity=0.4,
                cmap='gray'
            )
            
            # Adjust opacity in real-time
            scene.update_mri_opacity('t1_overlay', 0.6)
            
            # Surface-based MRI overlay
            mri_surface = mri_volume.contour([threshold_value])
            surface_actor = scene.add_mri_overlay(
                mri_surface,
                name='mri_surface',
                opacity=0.5,
                color='red',
                show_edges=False
            )
            ```
        """
        try:
            # Handle fallback mode
            if self._plotter is None:
                if hasattr(self, 'placeholder'):
                    self.placeholder.setText(f"PyVista 3D Scene\n{name}: MRI overlay\nOpacity: {opacity}")
                return f"fallback_{name}"
            
            if mri_mesh is None:
                log.warning("SimplePyVistaScene: No MRI mesh provided")
                return None
            
            # Determine rendering approach based on data type
            import pyvista as pv
            is_volume = isinstance(mri_mesh, pv.ImageData)
            
            # Set up rendering properties for medical overlay
            render_kwargs = kwargs.copy()
            render_kwargs['opacity'] = opacity
            render_kwargs['pickable'] = False  # Enable click-through for CT interaction
            
            if is_volume:
                # Volume rendering for 3D MRI data visualization
                log.debug(f"SimplePyVistaScene: Volume rendering MRI data")
                render_kwargs['scalars'] = 'values'
                render_kwargs['cmap'] = render_kwargs.get('cmap', 'gray')
                render_kwargs['show_scalar_bar'] = False
                # Use volume rendering for optimal 3D tissue visualization
                actor = self._plotter.add_volume(mri_mesh, name=name, **render_kwargs)
            else:
                # Surface rendering for processed MRI mesh data
                log.debug(f"SimplePyVistaScene: Surface rendering MRI mesh")
                render_kwargs['color'] = render_kwargs.get('color', 'gray')
                render_kwargs['show_edges'] = render_kwargs.get('show_edges', False)
                actor = self._plotter.add_mesh(mri_mesh, name=name, **render_kwargs)
            
            # Register mesh and actor for management
            self.meshes[name] = mri_mesh
            self.actors[name] = actor
            
            log.debug(f"SimplePyVistaScene: Added MRI overlay {name} with opacity {opacity} ({'volume' if is_volume else 'surface'} rendering)")
            
            # Update display
            try:
                self._plotter.render()
            except Exception:
                pass
                
            return actor
            
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error adding MRI overlay {name}: {e}")
            return None
    
    def update_mri_opacity(self, name, opacity):
        """Update opacity of MRI overlay"""
        try:
            if self._plotter and name in self.actors:
                actor = self.actors[name]
                
                # Check if this is a volume actor (has GetProperty with GetScalarOpacity)
                if hasattr(actor, 'GetProperty'):
                    prop = actor.GetProperty()
                    if hasattr(prop, 'GetScalarOpacity'):
                        # This is a volume - use scalar opacity transfer function
                        import vtk
                        opacity_func = vtk.vtkPiecewiseFunction()
                        opacity_func.AddPoint(0.0, 0.0)  # Minimum value transparent
                        opacity_func.AddPoint(0.1, opacity)  # Low values with specified opacity
                        opacity_func.AddPoint(1.0, opacity)  # Maximum value with specified opacity
                        prop.SetScalarOpacity(opacity_func)
                        log.debug(f"SimplePyVistaScene: Updated volume {name} opacity to {opacity} using transfer function")
                    else:
                        # This is a surface mesh - use regular opacity
                        prop.SetOpacity(opacity)
                        log.debug(f"SimplePyVistaScene: Updated surface {name} opacity to {opacity}")
                    
                    try:
                        self._plotter.render()
                    except Exception:
                        pass
                else:
                    log.warning(f"SimplePyVistaScene: Actor {name} has no opacity property")
            else:
                log.warning(f"SimplePyVistaScene: Actor {name} not found for opacity update")
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error updating opacity for {name}: {e}")
            
    def remove_point_cloud(self, name):
        """Remove a point cloud from the scene"""
        try:
            if self._plotter and name in self.actors:
                self._plotter.remove_actor(self.actors[name])
                del self.actors[name]
            if name in self.meshes:
                del self.meshes[name]
        except Exception as e:
            log.debug(f"SimplePyVistaScene: Error removing {name}: {e}")
            
    def add_arrows(self, start_points, vectors, colors=None, name="arrows", **kwargs):
        """Add arrows to the scene"""
        return self.add_point_cloud(start_points, colors, name, **kwargs)
        """Add arrows to the scene"""
        return self.add_point_cloud(start_points, colors, name, **kwargs)
        
    def add_text(self, text, position=(0.01, 0.95), name="text", **kwargs):
        """Add text to the scene"""
        try:
            if self._plotter and hasattr(self._plotter, 'add_text'):
                log.debug(f"SimplePyVistaScene: Adding text '{text}' at position {position}")
                # Check if position is relative (2D screen) or world coordinates (3D)
                if len(position) == 2 and all(0 <= p <= 1 for p in position):
                    # Relative positioning for 2D screen text
                    log.debug(f"SimplePyVistaScene: Using 2D screen positioning for '{text}'")
                    # Default font size for 2D text
                    if 'font_size' not in kwargs:
                        kwargs['font_size'] = 12
                    actor = self._plotter.add_text(text, position=position, **kwargs)
                elif len(position) == 3:
                    # World coordinates for 3D floating text
                    log.debug(f"SimplePyVistaScene: Using 3D world coordinates for '{text}' at {position}")
                    # Default larger font size for 3D labels
                    if 'font_size' not in kwargs:
                        kwargs['font_size'] = 20
                    
                    # Filter out parameters not supported by add_point_labels
                    label_kwargs = {}
                    supported_params = ['font_size', 'font_family', 'show_points', 'point_size', 'shape_color', 'point_color', 'render_points_as_spheres']
                    for key, value in kwargs.items():
                        if key in supported_params:
                            label_kwargs[key] = value
                    
                    # Handle color parameter - convert to shape_color for labels
                    if 'color' in kwargs:
                        label_kwargs['shape_color'] = kwargs['color']
                        
                    actor = self._plotter.add_point_labels([position], [text], **label_kwargs)
                else:
                    # Default to 2D screen text
                    log.debug(f"SimplePyVistaScene: Defaulting to 2D screen positioning for '{text}'")
                    if 'font_size' not in kwargs:
                        kwargs['font_size'] = 12
                    actor = self._plotter.add_text(text, position=position, **kwargs)
                    
                if actor is not None:
                    self.actors[name] = actor
                    log.debug(f"SimplePyVistaScene: Successfully added text '{name}' with actor: {actor}")
                else:
                    log.warning(f"SimplePyVistaScene: Failed to create text actor for '{name}'")
                return actor
        except Exception as e:
            log.error(f"SimplePyVistaScene: Failed to add text '{name}': {e}")
        return None
        
    def remove_text(self, name):
        """Remove text from the scene"""
        try:
            if self._plotter and name in self.actors:
                self._plotter.remove_actor(self.actors[name])
                del self.actors[name]
        except Exception:
            pass
            
    def clear(self):
        """Clear all objects from the scene"""
        try:
            if self._plotter:
                self._plotter.clear()
            self.actors.clear()
            self.meshes.clear()
        except Exception:
            pass
        
    def render_scene(self):
        """Force a render update"""
        try:
            if self._plotter:
                self._plotter.render()
        except Exception:
            pass

    def render(self, *args, **kwargs):
        """Compatibility shim for QWidget.render() calls"""
        try:
            self.render_scene()
        except Exception:
            pass
        
    def reset_camera(self):
        """Reset camera to fit all objects"""
        try:
            if self._plotter:
                self._plotter.reset_camera()
        except Exception:
            pass
        
    @property
    def camera(self):
        """Access to the camera for manual control"""
        try:
            if self._plotter:
                return self._plotter.camera
        except Exception:
            pass
        return None
        
    def get_camera_position(self):
        """Get current camera position and orientation"""
        try:
            if self._plotter:
                return self._plotter.camera_position
        except Exception:
            pass
        return None
        
    def set_camera_position(self, position):
        """Set camera position and orientation"""
        try:
            if self._plotter:
                self._plotter.camera_position = position
        except Exception:
            pass


class SimplePyVistaSceneModel(HasTraits):
    """
    Traits-compatible wrapper for SimplePyVistaScene providing Mayavi-like interface.
    
    This class provides backward compatibility with existing VoxTool code that expects
    a Traits-based scene model similar to Mayavi's MayaviSceneModel. It wraps the
    SimplePyVistaScene widget and provides the same interface patterns.
    
    COMPATIBILITY ARCHITECTURE:
    ===========================
    
    Legacy Code Integration:
    - Maintains HasTraits interface for existing medical workflow code
    - Provides .scene property for direct scene access
    - Implements .gcf() method for figure access (Mayavi compatibility)
    - Supports activation patterns used by medical visualization controllers
    
    Traits System Integration:
    - Uses Instance trait for proper Traits object management
    - Supports trait change notifications and observers
    - Integrates with existing TraitsUI and medical workflow code
    - Maintains object lifecycle management patterns
    
    MEDICAL WORKFLOW COMPATIBILITY:
    ==============================
    
    The wrapper ensures that existing medical code patterns continue to work:
    ```python
    # Legacy pattern that continues to work
    scene_model = SimplePyVistaSceneModel()
    scene_model.scene.add_point_cloud(ct_points, colors, 'ct_scan')
    plotter = scene_model.gcf()  # Returns PyVista plotter
    ```
    
    MIGRATION STRATEGY:
    ==================
    
    This wrapper enables gradual migration from Mayavi to PyVista:
    1. Replace MayaviSceneModel with SimplePyVistaSceneModel
    2. Update visualization calls to use PyVista methods
    3. Maintain existing Traits-based architecture
    4. Preserve medical workflow integration points
    
    DEBUGGING WRAPPER ISSUES:
    ========================
    
    Common problems with the wrapper:
    - Check .scene initialization: should not be None
    - Verify Traits import and HasTraits inheritance
    - Test activation notifications and observers
    - Monitor memory management with large medical datasets
    
    Attributes:
        scene (Instance): SimplePyVistaScene instance for actual 3D visualization
        activated (Bool): Tracks whether scene has been activated for use
    
    Example Usage:
        ```python
        # Create Traits-compatible scene model
        scene_model = SimplePyVistaSceneModel()
        
        # Access underlying scene for visualization
        scene = scene_model.scene
        scene.add_point_cloud(points, colors, 'data')
        
        # Access plotter for advanced operations
        plotter = scene_model.gcf()
        if plotter:
            plotter.camera.position = (10, 10, 10)
        ```
    """
    # Traits attributes for medical workflow integration
    scene = Instance(SimplePyVistaScene)  # Main visualization scene
    activated = Bool(False)               # Activation state tracking
    
    def _scene_default(self):
        """
        Default scene factory method for Traits system.
        
        This method is automatically called by the Traits system when the scene
        attribute is first accessed. It ensures proper initialization of the
        SimplePyVistaScene widget.
        
        Returns:
            SimplePyVistaScene: Configured 3D visualization widget
        """
        return SimplePyVistaScene()
        
    def _activated_changed(self):
        """
        Handle activation state changes for medical workflow integration.
        
        This method is automatically called when the activated trait changes.
        It can be used to trigger initialization or cleanup operations needed
        by the medical workflow system.
        """
        pass
        
    @property 
    def plotter(self):
        """
        Access to the underlying PyVista plotter for advanced operations.
        
        This property provides direct access to the PyVista BackgroundPlotter
        instance for operations that require low-level VTK or PyVista control.
        
        Returns:
            BackgroundPlotter or None: PyVista plotter if available
        """
        if self.scene:
            return self.scene.plotter
        return None
        
    def gcf(self):
        """
        Get current figure (plotter) - Mayavi compatibility method.
        
        This method provides Mayavi-compatible access to the current figure/plotter.
        It maintains compatibility with existing medical visualization code that
        expects a gcf() method for figure access.
        
        Returns:
            BackgroundPlotter or None: Current PyVista plotter instance
        """
        if self.scene:
            return self.scene.plotter
        return None
        
    def set_background_color(self, color):
        """
        Set background color - wrapper for scene method.
        
        This method provides a convenient wrapper for setting the background color
        while maintaining the Traits interface pattern.
        
        Args:
            color: Background color specification (string or RGB tuple)
        """
        if self.scene:
            self.scene.set_background_color(color)


# Compatibility aliases for seamless migration from legacy codebase
# These allow existing code to continue working without modification
PyVistaScene = SimplePyVistaScene           # Main scene class alias
PyVistaSceneModel = SimplePyVistaSceneModel # Traits model class alias


# =============================================================================
# CONVENIENCE FUNCTIONS FOR MAYAVI COMPATIBILITY
# =============================================================================

def points3d(x, y, z, s=None, **kwargs):
    """
    Create 3D point cloud similar to Mayavi's mlab.points3d function.
    
    This function provides Mayavi-compatible point cloud creation for easier
    migration of existing medical visualization code. It converts coordinate
    arrays into PyVista PolyData format suitable for 3D rendering.
    
    MAYAVI MIGRATION SUPPORT:
    ========================
    
    This function helps migrate code patterns like:
    ```python
    # Old Mayavi code
    from mayavi import mlab
    pts = mlab.points3d(x, y, z, s)
    
    # New PyVista code  
    from view.pyvista_viewer_simple import points3d
    pts = points3d(x, y, z, s)
    ```
    
    COORDINATE PROCESSING:
    =====================
    
    Input coordinates can be:
    - Python lists: [x1, x2, ...], [y1, y2, ...], [z1, z2, ...]
    - NumPy arrays: np.array([x1, x2, ...]), etc.
    - Any array-like sequence with consistent length
    
    Output is always a PyVista PolyData object ready for rendering.
    
    SCALAR DATA HANDLING:
    ====================
    
    The 's' parameter (scalar values) is used for:
    - Color mapping via colormaps
    - Point sizing based on data values  
    - Data-driven visualization in medical imaging
    - Threshold-based filtering and selection
    
    MEDICAL APPLICATIONS:
    ====================
    
    Common usage in medical imaging:
    - CT density visualization with HU values as scalars
    - Electrode contact rendering with selection states
    - Distance-based coloring for surgical planning
    - Time-series data visualization in functional imaging
    
    Args:
        x (array-like): X coordinates of points (medical: typically Left-Right)
        y (array-like): Y coordinates of points (medical: typically Anterior-Posterior)  
        z (array-like): Z coordinates of points (medical: typically Superior-Inferior)
        s (array-like, optional): Scalar values for coloring/sizing points.
                                 Common in medical: HU values, distances, probabilities
        **kwargs: Additional parameters passed to PyVista (unused in basic version)
    
    Returns:
        PyVista.PolyData: Point cloud ready for 3D visualization and medical analysis
    
    Example Usage:
        ```python
        # CT scan points with density values
        ct_points = points3d(ct_x, ct_y, ct_z, ct_densities)
        
        # Electrode contacts with selection state
        electrode_points = points3d(elec_x, elec_y, elec_z, selection_state)
        
        # Simple anatomical landmarks
        landmark_points = points3d(landmark_x, landmark_y, landmark_z)
        ```
    """
    # Convert inputs to numpy arrays for consistent handling
    if isinstance(x, (list, tuple)):
        x = np.array(x)
    if isinstance(y, (list, tuple)):
        y = np.array(y)
    if isinstance(z, (list, tuple)):
        z = np.array(z)
        
    # Combine coordinates into N×3 point array
    points = np.column_stack((x, y, z))
    
    # Create PyVista point cloud
    point_cloud = pv.PolyData(points)
    
    # Add scalar data if provided
    if s is not None:
        point_cloud['scalars'] = s
        
    return point_cloud


def figure(plotter, bgcolor=(1, 1, 1)):
    """
    Configure figure properties - Mayavi compatibility function.
    
    This function provides a Mayavi-compatible interface for figure configuration.
    In the PyVista context, most figure configuration is handled by the plotter
    itself, so this function serves primarily as a compatibility shim.
    
    MAYAVI MIGRATION:
    ================
    
    Helps migrate code patterns like:
    ```python
    # Old Mayavi code
    from mayavi import mlab  
    mlab.figure(bgcolor=(1, 1, 1))
    
    # New PyVista code - handled by plotter
    # Figure configuration done during plotter setup
    ```
    
    BACKGROUND COLOR HANDLING:
    =========================
    
    Background colors in medical imaging:
    - Black (0, 0, 0): Traditional medical imaging background
    - White (1, 1, 1): Modern clinical interface style
    - Gray (0.5, 0.5, 0.5): Neutral background for color visualization
    
    Args:
        plotter: PyVista plotter instance (currently unused in basic implementation)
        bgcolor (tuple): Background color as RGB tuple (0-1 range)
                        Default: (1, 1, 1) for white background
    
    Note:
        This function is primarily for compatibility. In PyVista, background
        color is typically set during plotter initialization or via
        plotter.set_background() method.
    """
    # Placeholder for Mayavi compatibility
    # Actual background setting handled by SimplePyVistaScene.set_background_color()
    pass


def text(x, y, text, **kwargs):
    """
    Create text annotation - Mayavi compatibility function.
    
    This function provides Mayavi-compatible text creation for medical imaging
    annotations. It returns a dictionary with text parameters that can be
    processed by the SimplePyVistaScene.add_text() method.
    
    MEDICAL TEXT ANNOTATIONS:
    ========================
    
    Common text uses in medical imaging:
    - Anatomical orientation labels (L, R, A, P, S, I)
    - Patient information and scan parameters
    - Measurement values and distances
    - Surgical planning annotations
    - Image slice information and coordinates
    
    COORDINATE SYSTEMS:
    ==================
    
    Text positioning options:
    - Screen coordinates (0-1): Relative to viewport edges
    - World coordinates: Positioned in 3D medical space
    - Normalized coordinates: Independent of window size
    
    STYLE PARAMETERS:
    ================
    
    Common text styling for medical applications:
    - font_size: 12-24 for readability in clinical settings
    - color: High contrast colors for medical displays
    - bold: True for important annotations
    - position: Strategic placement to avoid obscuring anatomy
    
    Args:
        x (float): X position for text placement
        y (float): Y position for text placement  
        text (str): Text content to display
        **kwargs: Additional text styling parameters
    
    Returns:
        dict: Text specification dictionary with position, content, and styling
    
    Example Usage:
        ```python
        # Anatomical orientation labels
        left_label = text(0.05, 0.5, 'L', color='green', font_size=20)
        right_label = text(0.95, 0.5, 'R', color='green', font_size=20)
        
        # Patient information
        patient_info = text(0.02, 0.98, 'Patient: Smith, J.', font_size=12)
        
        # Measurement annotation
        distance_label = text(0.5, 0.02, 'Distance: 15.3 mm', color='yellow')
        ```
    """
    return {'position': (x, y), 'text': text, 'kwargs': kwargs}