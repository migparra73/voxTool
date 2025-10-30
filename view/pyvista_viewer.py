"""
PyVista-based 3D visualization components to replace Mayavi
"""

import numpy as np
import pyvista as pv
import pyvistaqt as pvqt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from traits.api import HasTraits, Instance, Bool
import logging

log = logging.getLogger(__name__)

class PyVistaScene(QWidget):
    """
    PyVista-based 3D scene widget that replaces MayaviScene
    """
    
    # Signal emitted when mouse picks a point in the scene
    point_picked = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout first
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Initialize plotter attribute
        self._plotter = None
        
        # Try to create a working PyVista widget
        try:
            # Method 1: Try BackgroundPlotter
            import pyvistaqt
            self._plotter = pyvistaqt.BackgroundPlotter()
            layout.addWidget(self._plotter)
            log.debug("PyVistaScene.__init__: Using BackgroundPlotter")
        except Exception as e1:
            try:
                # Method 2: Try MainWindow 
                self._plotter = pv.Plotter()
                self.qt_widget = pyvistaqt.MainWindow()
                layout.addWidget(self.qt_widget)
                log.debug("PyVistaScene.__init__: Using MainWindow")
            except Exception as e2:
                # Method 3: Try basic approach - just create a placeholder
                try:
                    from PySide6.QtWidgets import QLabel
                    placeholder = QLabel("PyVista initialization failed")
                    layout.addWidget(placeholder)
                    self._plotter = None
                    log.error(f"PyVistaScene.__init__: All plotter creation methods failed: {e1}, {e2}")
                except Exception as e3:
                    log.error(f"PyVistaScene.__init__: Complete failure: {e1}, {e2}, {e3}")
                    self._plotter = None
        
        # Store references to plotted objects
        self.actors = {}
        self.meshes = {}
        
        # Configure basic settings
        try:
            self.qt_interactor.set_background('white')
            self.qt_interactor.show_axes()
            log.debug("PyVistaScene.__init__: Basic configuration successful")
        except Exception as e:
            log.debug(f"PyVistaScene.__init__: Basic configuration failed: {e}")
        
        # Mouse picking callback
        log.debug("PyVistaScene.__init__: Enabling point picking...")
        try:
            # Enable point picking if available
            if hasattr(self.qt_interactor, 'enable_point_picking'):
                self.qt_interactor.enable_point_picking(callback=self._on_point_picked, show_message=False)
                log.debug("PyVistaScene.__init__: Point picking enabled")
        except Exception as e:
            log.warning(f"PyVistaScene.__init__: Point picking failed: {e}")
    
    @property
    def plotter(self):
        """Access to the underlying plotter through the Qt interactor"""
        return self.qt_interactor
            
    def _on_mesh_picked(self, mesh, pid):
        """Handle mesh picking events (fallback for point picking)"""
        if pid is not None and mesh is not None:
            try:
                point = mesh.points[pid]
                log.debug(f"PyVistaScene._on_mesh_picked: Mesh picked at point {point}")
                self.point_picked.emit(point)
            except Exception as e:
                log.warning(f"PyVistaScene._on_mesh_picked: Error processing mesh pick: {e}")
        
    def _on_point_picked(self, point):
        """Handle point picking events"""
        log.debug(f"PyVistaScene._on_point_picked: Point picked at {point}")
        self.point_picked.emit(point)
        
    def set_background_color(self, color):
        """Set background color (RGB tuple or color name)"""
        try:
            self.qt_interactor.set_background(color)
        except Exception as e:
            log.debug(f"PyVistaScene.set_background_color: Failed to set background: {e}")
        
    def add_point_cloud(self, points, colors=None, name="points", **kwargs):
        """
        Add a point cloud to the scene
        
        Parameters:
        -----------
        points : array-like, shape (N, 3)
            3D coordinates of points
        colors : array-like, optional
            Colors for each point
        name : str
            Unique name for this point cloud
        **kwargs : dict
            Additional arguments passed to pyvista.
            Use 'constant_size': True to enable zoom-independent point sizes
        """
        # Ensure points are in the correct format (float32)
        points = np.asarray(points, dtype=np.float32)
        
        # Create point cloud mesh
        point_cloud = pv.PolyData(points)
        
        # Add colors if provided
        if colors is not None:
            colors = np.asarray(colors)
            
            # Check if colors are RGB (N x 3) or scalar (N,)
            if colors.ndim == 2 and colors.shape[1] == 3:
                # RGB colors - convert to 0-255 range if needed
                if colors.max() <= 1.0:
                    colors = (colors * 255).astype(np.uint8)
                point_cloud['RGB'] = colors
                log.debug(f"PyVistaScene.add_point_cloud: Added {len(colors)} RGB colors")
            else:
                # Scalar colors
                point_cloud['scalars'] = colors
                log.debug(f"PyVistaScene.add_point_cloud: Added {len(colors)} scalar colors")
        
        # Check if constant size is requested
        constant_size = kwargs.get('constant_size', False)
        
        # If constant size is requested, use glyph-based rendering with proper scaling
        if constant_size or kwargs.get('mode') == 'cube':
            # Create sphere glyphs for constant-size rendering
            sphere = pv.Sphere(radius=kwargs.get('point_size', 5) * 0.01)  # Scale factor for visual size
            
            # Apply glyph filter - this ensures consistent size regardless of camera distance
            try:
                glyphed = point_cloud.glyph(geom=sphere, scale=False)  # scale=False is key for constant size
                
                # Set up render options for glyphs
                render_options = {
                    'opacity': kwargs.get('opacity', 1.0),
                }
                
                # Handle colors for glyphs - simplified approach
                if colors is not None and colors.ndim == 2 and colors.shape[1] == 3:
                    # For RGB colors with glyphs, we use a simpler approach
                    render_options['color'] = colors[0] if len(colors) > 0 else [1.0, 1.0, 1.0]
                    render_options['rgb'] = False  # Use single color for now
                elif colors is not None:
                    # Scalar colors work directly with glyph
                    render_options['scalars'] = 'scalars'
                    render_options['cmap'] = kwargs.get('cmap', 'viridis')
                
                log.debug(f"PyVistaScene.add_point_cloud: Using glyph-based constant-size rendering for {name}")
                
                # Add the glyphed mesh
                actor = self.qt_interactor.add_mesh(glyphed, name=name, **render_options)
                self.meshes[name] = glyphed
                
            except Exception as e:
                log.warning(f"PyVistaScene.add_point_cloud: Glyph rendering failed: {e}, falling back to points")
                # Fallback to standard point rendering
                constant_size = False
            
        if not constant_size:
            # Standard point rendering (will scale with zoom)
            render_options = {
                'style': 'points',
                'point_size': kwargs.get('point_size', 5),
                'opacity': kwargs.get('opacity', 1.0),
                'render_points_as_spheres': True,  # Enable better point rendering
            }
            
            # Use RGB colors if available, otherwise use scalars with colormap
            if colors is not None:
                if colors.ndim == 2 and colors.shape[1] == 3:
                    render_options['rgb'] = True  # Use RGB colors directly
                else:
                    render_options['scalars'] = 'scalars'
                    render_options['cmap'] = kwargs.get('cmap', 'viridis')
            
            log.debug(f"PyVistaScene.add_point_cloud: Using standard point rendering for {name}")
            
            # Add to plotter
            try:
                actor = self.qt_interactor.add_mesh(point_cloud, name=name, **render_options)
                self.meshes[name] = point_cloud
            except Exception as e:
                log.error(f"PyVistaScene.add_point_cloud: Failed to add mesh: {e}")
                return None
        
        # Store references
        if 'actor' in locals():
            self.actors[name] = actor
        
        return actor if 'actor' in locals() else None
        
    def update_point_cloud(self, name, points, colors=None, **kwargs):
        """Update an existing point cloud"""
        if name in self.actors:
            self.remove_point_cloud(name)
        return self.add_point_cloud(points, colors, name, **kwargs)
        
    def remove_point_cloud(self, name):
        """Remove a point cloud from the scene"""
        try:
            if name in self.actors:
                self.qt_interactor.remove_actor(self.actors[name])
                del self.actors[name]
            if name in self.meshes:
                del self.meshes[name]
        except Exception as e:
            log.debug(f"PyVistaScene.remove_point_cloud: Error removing {name}: {e}")
            
    def add_arrows(self, start_points, vectors, colors=None, name="arrows", **kwargs):
        """
        Add arrows to the scene (for coordinate axes)
        """
        try:
            arrows = pv.PolyData(start_points)
            arrows['vectors'] = vectors
            
            if colors is not None:
                arrows['colors'] = colors
                
            # Create arrow glyphs
            arrow_glyph = arrows.glyph(orient='vectors', scale='vectors', factor=kwargs.get('scale_factor', 1.0))
            
            render_options = {
                'opacity': kwargs.get('opacity', 1.0),
                'cmap': kwargs.get('cmap', 'viridis'),
            }
            
            actor = self.qt_interactor.add_mesh(arrow_glyph, name=name, **render_options)
            
            self.actors[name] = actor
            self.meshes[name] = arrow_glyph
            
            return actor
        except Exception as e:
            log.error(f"PyVistaScene.add_arrows: Failed to add arrows: {e}")
            return None
        
    def add_text(self, text, position=(0.01, 0.95), name="text", **kwargs):
        """Add text to the scene"""
        try:
            # Convert relative position to screen coordinates if needed
            if all(0 <= p <= 1 for p in position):
                # Relative positioning
                actor = self.qt_interactor.add_text(text, position=position, viewport=True, **kwargs)
            else:
                # World coordinates
                actor = self.qt_interactor.add_point_labels([position], [text], **kwargs)
                
            self.actors[name] = actor
            return actor
        except Exception as e:
            log.debug(f"PyVistaScene.add_text: Failed to add text: {e}")
            return None
        
    def remove_text(self, name):
        """Remove text from the scene"""
        try:
            if name in self.actors:
                self.qt_interactor.remove_actor(self.actors[name])
                del self.actors[name]
        except Exception as e:
            log.debug(f"PyVistaScene.remove_text: Error removing text {name}: {e}")
            
    def clear(self):
        """Clear all objects from the scene"""
        try:
            self.qt_interactor.clear()
            self.actors.clear()
            self.meshes.clear()
        except Exception as e:
            log.debug(f"PyVistaScene.clear: Error clearing scene: {e}")
        
    def render_scene(self):
        """Force a render update"""
        try:
            self.qt_interactor.render()
        except Exception as e:
            log.debug(f"PyVistaScene.render_scene: Error rendering: {e}")
        
    def reset_camera(self):
        """Reset camera to fit all objects"""
        try:
            self.qt_interactor.reset_camera()
        except Exception as e:
            log.debug(f"PyVistaScene.reset_camera: Error resetting camera: {e}")
        
    @property
    def camera(self):
        """Access to the camera for manual control"""
        try:
            return self.qt_interactor.camera
        except Exception as e:
            log.debug(f"PyVistaScene.camera: Error accessing camera: {e}")
            return None
        
    def get_camera_position(self):
        """Get current camera position and orientation"""
        try:
            return self.qt_interactor.camera_position
        except Exception as e:
            log.debug(f"PyVistaScene.get_camera_position: Error getting camera position: {e}")
            return None
        
    def set_camera_position(self, position):
        """Set camera position and orientation"""
        try:
            self.qt_interactor.camera_position = position
        except Exception as e:
            log.debug(f"PyVistaScene.set_camera_position: Error setting camera position: {e}")


class PyVistaSceneModel(HasTraits):
    """
    Traits-compatible wrapper for PyVistaScene to replace MlabSceneModel
    """
    scene = Instance(PyVistaScene)
    activated = Bool(False)  # Required by TraitsUI
    
    def _scene_default(self):
        """Default scene factory"""
        return PyVistaScene()
        
    def _activated_changed(self):
        """Called when scene is activated"""
        # Trigger any necessary initialization
        pass
        
    @property 
    def plotter(self):
        """Access to the underlying PyVista plotter"""
        if self.scene:
            return self.scene.plotter
        return None
        
    def gcf(self):
        """Get current figure (plotter) - for compatibility with mayavi"""
        if self.scene:
            return self.scene.plotter
        return None
        
    def set_background_color(self, color):
        """Set background color"""
        if self.scene:
            self.scene.set_background_color(color)


# Convenience functions that mimic mlab interface
def points3d(x, y, z, s=None, **kwargs):
    """
    Create 3D points similar to mlab.points3d
    Returns a mesh that can be added to a PyVistaScene
    """
    # Combine coordinates
    if isinstance(x, (list, tuple)):
        x = np.array(x)
    if isinstance(y, (list, tuple)):
        y = np.array(y)
    if isinstance(z, (list, tuple)):
        z = np.array(z)
        
    points = np.column_stack((x, y, z))
    
    # Create point cloud
    point_cloud = pv.PolyData(points)
    
    # Add scalar data if provided
    if s is not None:
        point_cloud['scalars'] = s
        
    return point_cloud


def figure(plotter, bgcolor=(1, 1, 1)):
    """Set figure properties - for compatibility with mayavi"""
    if plotter:
        try:
            plotter.set_background(bgcolor)
        except Exception as e:
            log.debug(f"figure: Error setting background: {e}")


def text(x, y, text, **kwargs):
    """Add text to the scene - for compatibility with mayavi"""
    # This will be handled by the scene's add_text method
    return {'position': (x, y), 'text': text, 'kwargs': kwargs}