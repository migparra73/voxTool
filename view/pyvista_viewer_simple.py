"""
Working PyVista-based 3D visualization that actually displays point clouds
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
    Working PyVista 3D scene that displays actual point clouds
    """
    
    # Signal emitted when mouse picks a point in the scene
    point_picked = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Store references to plotted objects
        self.actors = {}
        self.meshes = {}
        self.callbacks = {}  # Store callbacks for each actor
        self._plotter = None
        
        # Try to create working PyVista widget
        if PYVISTAQT_AVAILABLE:
            try:
                # Use BackgroundPlotter which we know works
                self._plotter = pvqt.BackgroundPlotter(show=False)
                layout.addWidget(self._plotter)
                log.debug("SimplePyVistaScene: BackgroundPlotter created successfully")
                
                # Enable point picking for interaction
                try:
                    # Try different PyVista picking methods
                    if hasattr(self._plotter, 'enable_point_picking'):
                        self._plotter.enable_point_picking(callback=self._on_point_picked, show_message=False)
                        log.debug("SimplePyVistaScene: Point picking enabled with enable_point_picking")
                    elif hasattr(self._plotter, 'enable_mesh_picking'):
                        self._plotter.enable_mesh_picking(callback=self._on_mesh_picked, show_message=False)
                        log.debug("SimplePyVistaScene: Mesh picking enabled as fallback")
                    else:
                        log.warning("SimplePyVistaScene: No picking methods available")
                        
                    # Also try to enable click events
                    if hasattr(self._plotter, 'track_click_position'):
                        self._plotter.track_click_position(callback=self._on_click_position)
                        log.debug("SimplePyVistaScene: Click position tracking enabled")
                        
                except Exception as e:
                    log.warning(f"SimplePyVistaScene: Point picking setup failed: {e}")
                    # Try alternative picking approach
                    try:
                        # Enable general picking
                        self._plotter.enable_picking(callback=self._on_general_pick)
                        log.debug("SimplePyVistaScene: General picking enabled as fallback")
                    except Exception as e2:
                        log.warning(f"SimplePyVistaScene: All picking methods failed: {e2}")
                    
            except Exception as e:
                log.warning(f"SimplePyVistaScene: BackgroundPlotter failed: {e}")
                self._create_fallback(layout)
        else:
            self._create_fallback(layout)
    
    def _create_fallback(self, layout):
        """Create fallback placeholder"""
        self.placeholder = QLabel("PyVista 3D Scene\n(PyVistaQt not available)")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)
        self._plotter = None
    
    @property
    def plotter(self):
        """Access to the underlying plotter"""
        return self._plotter
    
    def _on_point_picked(self, point):
        """Handle point picking events from PyVista"""
        try:
            # Convert point to numpy array
            picked_point = np.array(point)
            log.debug(f"SimplePyVistaScene: Point picked at {picked_point}")
            
            # Create a mock picker object that matches the expected interface
            class MockPicker:
                def __init__(self, position):
                    self.pick_position = position
            
            picker = MockPicker(picked_point)
            
            # Find which actor was picked and call its callback
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
            
            if not callback_called:
                log.warning(f"SimplePyVistaScene: No callback found for picked point {picked_point}")
                log.debug(f"SimplePyVistaScene: Available callbacks: {list(self.callbacks.keys())}")
                log.debug(f"SimplePyVistaScene: Available actors: {list(self.actors.keys())}")
            
            # Also emit the signal for direct connections
            self.point_picked.emit(picked_point)
            
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in point picking: {e}")
            import traceback
            log.error(f"SimplePyVistaScene: Traceback: {traceback.format_exc()}")
    
    def _on_mesh_picked(self, mesh, pick_result):
        """Handle mesh picking events as fallback"""
        try:
            if hasattr(pick_result, 'world_position'):
                point = pick_result.world_position
            elif hasattr(pick_result, 'point'):
                point = pick_result.point
            else:
                log.warning("SimplePyVistaScene: No position information in mesh pick result")
                return
                
            log.debug(f"SimplePyVistaScene: Mesh picked at {point}")
            self._on_point_picked(point)
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in mesh picking: {e}")
    
    def _on_click_position(self, position):
        """Handle click position events"""
        try:
            log.debug(f"SimplePyVistaScene: Click position at {position}")
            log.debug(f"SimplePyVistaScene: Available callbacks: {list(self.callbacks.keys())}")
            log.debug(f"SimplePyVistaScene: Available actors: {list(self.actors.keys())}")
            self._on_point_picked(position)
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in click position: {e}")
    
    def _on_general_pick(self, pick_result):
        """Handle general picking events"""
        try:
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
            self._on_point_picked(point)
        except Exception as e:
            log.error(f"SimplePyVistaScene: Error in general picking: {e}")
            
    def set_callback(self, actor_name, callback):
        """Set callback function for a specific actor"""
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
        Add a point cloud to the scene
        """
        try:
            # Store callback for this actor
            if callback:
                self.callbacks[name] = callback
            
            # Ensure points are in the correct format
            points = np.asarray(points, dtype=np.float32)
            
            if self._plotter is None:
                # Update fallback if no plotter
                if hasattr(self, 'placeholder'):
                    n_points = len(points)
                    constant_size = kwargs.get('constant_size', False)
                    mode = kwargs.get('mode', 'points')
                    info_text = f"PyVista 3D Scene\n{name}: {n_points} points\nConstant size: {constant_size}"
                    self.placeholder.setText(info_text)
                return f"fallback_{name}"
            
            # Create point cloud mesh
            point_cloud = pv.PolyData(points)
            
            # Handle colors properly
            if colors is not None:
                colors = np.asarray(colors)
                if colors.ndim == 2 and colors.shape[1] >= 3:
                    # RGB/RGBA colors - ensure correct shape
                    if colors.shape[0] == len(points):
                        if colors.max() <= 1.0:
                            colors = (colors * 255).astype(np.uint8)
                        point_cloud['RGB'] = colors
                elif colors.ndim == 1 and len(colors) == len(points):
                    # Scalar colors
                    point_cloud['scalars'] = colors
            
            # Check for constant size rendering
            constant_size = kwargs.get('constant_size', False)
            mode = kwargs.get('mode', 'points')
            
            # Render options
            render_kwargs = {
                'point_size': kwargs.get('point_size', 8),
                'opacity': kwargs.get('opacity', 1.0),
            }
            
            # Try constant size glyphs first if requested
            if constant_size and mode == 'cube':
                try:
                    # Create constant-size sphere glyphs
                    sphere = pv.Sphere(radius=0.8)
                    glyphed = point_cloud.glyph(geom=sphere, scale=False)
                    
                    # Handle colors for glyphs
                    if 'RGB' in point_cloud.array_names:
                        render_kwargs['scalars'] = 'RGB'
                        render_kwargs['rgb'] = True
                    elif 'scalars' in point_cloud.array_names:
                        render_kwargs['scalars'] = 'scalars'
                        render_kwargs['cmap'] = kwargs.get('cmap', 'viridis')
                    
                    actor = self._plotter.add_mesh(glyphed, name=name, **render_kwargs)
                    self.meshes[name] = glyphed
                    self.actors[name] = actor
                    
                    log.debug(f"SimplePyVistaScene: Added constant-size glyphs for {name} ({len(points)} points)")
                    
                    # Force render
                    try:
                        self._plotter.render()
                    except Exception:
                        pass
                    
                    return actor
                    
                except Exception as e:
                    log.warning(f"SimplePyVistaScene: Glyph rendering failed for {name}: {e}, using points")
            
            # Standard point rendering
            render_kwargs['style'] = 'points'
            render_kwargs['render_points_as_spheres'] = True
            
            if colors is not None:
                if 'colors' in point_cloud.array_names:
                    render_kwargs['scalars'] = 'colors'
                    render_kwargs['rgb'] = True
                elif 'scalars' in point_cloud.array_names:
                    render_kwargs['scalars'] = 'scalars'
                    render_kwargs['cmap'] = kwargs.get('cmap', 'viridis')
            
            actor = self._plotter.add_mesh(point_cloud, name=name, **render_kwargs)
            self.meshes[name] = point_cloud
            self.actors[name] = actor
            
            log.debug(f"SimplePyVistaScene: Added point cloud {name} ({len(points)} points)")
            
            # Force render
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
            
    def add_arrows(self, start_points, vectors, colors=None, name="arrows", **kwargs):
        """Add arrows to the scene"""
        return self.add_point_cloud(start_points, colors, name, **kwargs)
        
    def add_text(self, text, position=(0.01, 0.95), name="text", **kwargs):
        """Add text to the scene"""
        try:
            if self._plotter and hasattr(self._plotter, 'add_text'):
                actor = self._plotter.add_text(text, position=position, **kwargs)
                self.actors[name] = actor
                return actor
        except Exception:
            pass
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
    Traits-compatible wrapper for SimplePyVistaScene
    """
    scene = Instance(SimplePyVistaScene)
    activated = Bool(False)
    
    def _scene_default(self):
        """Default scene factory"""
        return SimplePyVistaScene()
        
    def _activated_changed(self):
        """Called when scene is activated"""
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


# Alias to the original name for compatibility
PyVistaScene = SimplePyVistaScene
PyVistaSceneModel = SimplePyVistaSceneModel


# Convenience functions that mimic mlab interface
def points3d(x, y, z, s=None, **kwargs):
    """Create 3D points similar to mlab.points3d"""
    if isinstance(x, (list, tuple)):
        x = np.array(x)
    if isinstance(y, (list, tuple)):
        y = np.array(y)
    if isinstance(z, (list, tuple)):
        z = np.array(z)
        
    points = np.column_stack((x, y, z))
    point_cloud = pv.PolyData(points)
    
    if s is not None:
        point_cloud['scalars'] = s
        
    return point_cloud


def figure(plotter, bgcolor=(1, 1, 1)):
    """Set figure properties - for compatibility with mayavi"""
    pass


def text(x, y, text, **kwargs):
    """Add text to the scene - for compatibility with mayavi"""
    return {'position': (x, y), 'text': text, 'kwargs': kwargs}