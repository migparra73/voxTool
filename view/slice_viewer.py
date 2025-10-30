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

    def __init__(self, parent=None, scan=None):
        QWidget.__init__(self, parent)
        self.label = QLabel('')
        data = scan.data if scan else None
        self.views = [
            SliceView(self, data, axis=0, subplot=111),  # Use single subplot (111) for each
            SliceView(self, data, axis=1, subplot=111),
            SliceView(self, data, axis=2, subplot=111)
        ]

        splitter = QSplitter(Qt.Orientation.Vertical)
        for view in self.views:
            # Set minimum size and size policy for each view
            view.setMinimumSize(200, 200)
            view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            splitter.addWidget(view)

        # Set equal sizes for all views in the splitter
        splitter.setSizes([100, 100, 100])

        self.ct = None
        # Use system colors instead of hardcoded black
        # Remove the hardcoded palette setting to use system theme
        # p = self.palette()
        # p.setColor(self.backgroundRole(), Qt.GlobalColor.black)
        # self.setPalette(p)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(splitter)

        FigureCanvas.updateGeometry(self)
        print("slice_viewer: SliceView constructor complete")

    def set_coordinate(self, coordinate):
        for slice_view in self.views:
            slice_view.coordinate = coordinate

    def set_image(self, image):
        for slice_view in self.views:
            slice_view.set_image(image)

    def set_label(self,label):
        self.label.setText('File: \n%s'%label)

    def update_slices(self):
        for slice_view in self.views:
            slice_view.plot()

print("slice_viewer: defining SliceView class...")
class SliceView(FigureCanvas):

    def __init__(self, parent, data, axis, subplot):
        # Get system colors from Qt palette
        if parent and hasattr(parent, 'palette'):
            palette = parent.palette()
        else:
            # Create a temporary widget to get default palette
            temp_widget = QWidget()
            palette = temp_widget.palette()
            
        bg_color = palette.color(palette.ColorRole.Window)
        text_color = palette.color(palette.ColorRole.WindowText)
        
        # Convert Qt colors to matplotlib format (0-1 range)
        bg_rgb = (bg_color.redF(), bg_color.greenF(), bg_color.blueF())
        text_rgb = (text_color.redF(), text_color.greenF(), text_color.blueF())
        
        # Create figure with system background color and tight layout
        self.figure = Figure(facecolor=bg_rgb, edgecolor=text_rgb)
        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)
        
        self.data = data
        self.axis = axis
        self.coordinate = np.zeros((3,))
        self.plotted_coordinate = np.zeros((3,))
        self.radius = 1
        self.plotted_radius = 1
        self.subplot = subplot
        
        # Create subplot with system colors and no margins
        self.ax = self.figure.add_subplot(subplot)
        self.ax.set_facecolor(bg_rgb)
        
        # Remove all margins and padding to maximize image size
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0, hspace=0, wspace=0)
        
        # Set text colors for axes
        self.ax.tick_params(colors=text_rgb)
        self.ax.xaxis.label.set_color(text_rgb)
        self.ax.yaxis.label.set_color(text_rgb)
        
        self.circ = None
        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)


    def set_image(self, image):
        self.image = image

    def set_axis(self, axis):
        self.axis = axis

    def plot(self):
        if self.axis is None or self.image is None:
            return
            
        # Get current system colors (may have changed since initialization)
        try:
            from PySide6.QtWidgets import QApplication, QWidget
            app = QApplication.instance()
            if app:
                # Create a temporary widget to access palette
                temp_widget = QWidget()
                palette = temp_widget.palette()
                bg_color = palette.color(palette.ColorRole.Window)
                bg_rgb = (bg_color.redF(), bg_color.greenF(), bg_color.blueF())
            else:
                bg_rgb = (0, 0, 0)  # fallback
        except:
            bg_rgb = (0, 0, 0)  # fallback
            
        plot_plane = [slice(0, self.image.shape[i]) for i in range(3)]
        plot_plane[self.axis] = int(self.coordinate[self.axis])
        
        plot_plane_tuple = tuple(plot_plane)

        plotted_image = self.image[plot_plane_tuple]
        plotted_image = np.flipud(plotted_image.T)
        
        # Clear the axes and remove all margins/ticks to maximize image space
        self.ax.cla()
        self.ax.set_position((0.0, 0.0, 1.0, 1.0))  # Use full figure area
        self.ax.axis('off')  # Turn off axes completely
        
        # Set the facecolor
        self.ax.set_facecolor(bg_rgb)
        
        # Display image with aspect='auto' to fill the available space
        self._plot = self.ax.imshow(plotted_image, cmap=plt.get_cmap('bone'), 
                                   aspect='auto', interpolation='bilinear')
        # Draw coordinate marker circle
        circl_coords = list(self.coordinate)
        del circl_coords[self.axis]
        radius = 10 if self.axis != 3 else 40

        if self.axis != 2:
            circl_coords[0], circl_coords[1] = circl_coords[0], plotted_image.shape[0] - circl_coords[1]
        else:
            circl_coords[1] = plotted_image.shape[0] - circl_coords[1]

        # Convert list to tuple for Circle constructor
        circle_center = tuple(circl_coords)
        self.circ = Circle(circle_center, radius=radius, edgecolor='r', fill=False, linewidth=2)
        self.ax.add_patch(self.circ)
        #plt.tight_layout()
        #self._plot = plt.imshow(self.image[plot_plane], colormap='bone')#, aspect='auto')
        #src = self._plot.mlab_source
        #src.x = 100*(src.x - src.x.min())/(src.x.max() - src.x.min())
        #src.y = 100*(src.y - src.y.min())/(src.x.max() - src.y.min())
        self.draw()


    #@on_trait_change('scene.activated')
    #def update(self):
    #    self.plot()

    #view = View(Item('scene', editor=SceneEditor(scene_class=MayaviScene),
    #                 height=250, width=300, show_label=False),
    #            resizable=True  # We need this to resize with the parent widget
    #            )

print("slice_viewer: module definition complete!")