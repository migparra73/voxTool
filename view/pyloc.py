print("pyloc: Starting imports...")

import os
import json

print("pyloc: importing traits.etsconfig...")
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt'
print("pyloc: ETSConfig OK")

print("pyloc: importing PySide6.QtWidgets...")
# Import PySide6 Qt classes directly instead of using pyface.qt
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QComboBox, 
                               QSlider, QMessageBox, QFileDialog,
                               QSizePolicy, QSplitter, QProgressBar, QCheckBox,
                               QSpinBox, QDoubleSpinBox, QLineEdit, QGroupBox,
                               QTabWidget, QScrollArea, QFrame, QTextEdit,
                               QListWidget, QAbstractItemView, QListWidgetItem)
print("pyloc: PySide6.QtWidgets OK")

print("pyloc: importing PySide6.QtCore...")
from PySide6.QtCore import Qt, QTimer, Signal, QItemSelectionModel
print("pyloc: PySide6.QtCore OK")

print("pyloc: importing PySide6.QtGui...")
from PySide6.QtGui import QKeySequence, QIcon, QPixmap, QShortcut
print("pyloc: PySide6.QtGui OK")

print("pyloc: importing model.scan...")
from model.scan import CT
print("pyloc: model.scan OK")

print("pyloc: importing view.slice_viewer...")
from view.slice_viewer import SliceViewWidget
print("pyloc: view.slice_viewer OK")

print("pyloc: importing pyvista...")
from view.pyvista_viewer_simple import PyVistaScene, PyVistaSceneModel
print("pyloc: pyvista OK")
print("pyloc: importing traits.api...")
from traits.api import HasTraits, Instance, on_trait_change
print("pyloc: traits.api OK")

print("pyloc: importing traitsui.api...")
from traitsui.api import View, Item
print("pyloc: traitsui.api OK")

print("pyloc: importing other modules...")
import random
import numpy as np
import logging
import yaml
import re
from datetime import datetime

from collections import OrderedDict
print("pyloc: other modules OK")

print("pyloc: setting up logging...")
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to ch
ch.setFormatter(formatter)

# Add ch to logger
log.addHandler(ch)
print("pyloc: logging setup OK")

print("pyloc: defining utility functions...")
def add_labeled_widget(layout, label, *widgets):
    sub_layout = QHBoxLayout()
    label_widget = QLabel(label)
    sub_layout.addWidget(label_widget)
    for widget in widgets:
        sub_layout.addWidget(widget)
    layout.addLayout(sub_layout)

print("pyloc: utility functions OK")

print("pyloc: defining PylocControl class...")
class PylocControl(object):
    """
    Main class for running VoxTool.
    """
    AUTOSAVE_FILE = "voxTool_autosave.json"
    
    def __init__(self, config=None):
        log.debug("Initializing PylocControl")
        if config == None:
            config = yaml.load(open("../model/config.yml"), Loader=yaml.SafeLoader)

        log.debug("Config: {}".format(config))
        log.debug("Starting application")
        
        # Create QApplication if it doesn't exist
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
            log.debug("Created new QApplication")
        else:
            log.debug("Using existing QApplication")
            
        self.view = PylocWidget(self, config) #: The base object for the GUI
        log.debug("View created")
        self.view.show()

        log.debug("View shown")
        self.window = QMainWindow()
        self.window.setCentralWidget(self.view)
        self.window.show()
        log.debug("Window shown")

        self.lead_window = None #: See ..self.define_leads and ..LeadDefinitionWidget

        self.ct = None #: See self.load_ct; instance of ..scan.CT
        self.config = config # Global configuration file

        log.debug("Assigning callbacks and shortcuts")
        self.assign_callbacks()
        self.assign_shortcuts()

        self.clicked_coordinate = np.zeros((3,))
        self.selected_coordinate = np.zeros((3,))

        self.selected_lead = None #: The lead currently being localized
        self.contact_label = ""
        self.lead_location = [0, 0]
        self.lead_group = 0

        self.seeding = False #: Toggled by self.toggle_seeding

        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.auto_save_state)
        self.autosave_timer.start(10000)  # Autosave every 5 minutes
        
        # Try to recover on startup
        self.try_recover_state()
        
        self.mri = None
        self.mri_filename = None

    def auto_save_state(self):
        """Automatically saves current program state"""
        try:
            if not self.ct:
                return
                
            state = {
                'ct_file': self.ct.filename,
                'threshold': self.ct.threshold,
                'leads': self.ct.to_dict(),
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.AUTOSAVE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
                
            log.debug(f"Auto-saved state to {self.AUTOSAVE_FILE}")
            
        except Exception as e:
            log.error(f"Auto-save failed: {str(e)}")

    def try_recover_state(self):
        """Attempts to recover from auto-save file on startup"""
        try:
            if os.path.exists(self.AUTOSAVE_FILE):
                log.info("Found auto-save file, prompting user for recovery")
                
                # Get timestamp from autosave file
                with open(self.AUTOSAVE_FILE, 'r') as f:
                    state = json.load(f)
                    timestamp = state.get('timestamp', 'unknown time')
                
                # Ask user if they want to recover
                reply = QMessageBox.question(
                    None,
                    'Recover Session',
                    f'Found auto-saved session from {timestamp}.\nWould you like to restore it?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Load CT scan if it exists
                    if os.path.exists(state['ct_file']):
                        self.load_ct(state['ct_file'])
                        self.ct.set_threshold(state['threshold'])
                        
                        # Restore leads and contacts
                        self.ct.from_dict(state['leads'])
                        
                        # Update UI
                        self.view.update_clouds()
                        self.view.contact_panel.update_contacts()
                        
                        log.info("Successfully recovered from auto-saved")
                        # Enable manual save thru UI
                        self.view.task_bar.save_button.setEnabled(True)
                    else:
                        QMessageBox.warning(
                            None,
                            'Recovery Error',
                            'CT file not found, could not recover session'
                        )
                        log.warning("CT file not found, skipping recovery")
                else:
                    log.info("User chose not to recover auto-saved session")
                    
        except Exception as e:
            log.error(f"Recovery failed: {str(e)}")
            QMessageBox.warning(
                None,
                'Recovery Error',
                f'Failed to recover auto-saved session: {str(e)}'
            )

    def interpolate_selected_lead(self):
        """
        Callback for "Interpolate" button in lead panel
        :return:
        """
        log.debug("Interpolating selected lead")
        self.ct.interpolate(self.selected_lead.label)
        log.debug("Interpolated, updating cloud...")
        self.view.update_cloud('_leads')
        log.debug("Cloud updated, updating contact panel...")
        self.view.contact_panel.set_chosen_leads(self.ct.get_leads())
        log.debug("Contact panel updated, interpolate_selected_lead complete.")

    def add_micro_contacts(self):
        """
        Callback for "Add micro_contact" button in lead panel
        :return:
        """
        log.debug("Adding micro contacts")
        self.ct.add_micro_contacts()
        log.debug("Micro contacts added, updating cloud...")
        self.view.update_cloud('_leads')
        log.debug("Cloud updated, updating contact panel...")
        self.view.contact_panel.set_chosen_leads(self.ct.get_leads())
        log.debug("Contact panel updated, add_micro_contacts complete.")

    def toggle_seeding(self):
        """
        Callback for "Seeding" button in lead panel
        :return:
        """
        log.debug("Toggling seeding")
        self.seeding = not self.seeding
        if self.seeding:
            log.debug("Seeding enabled")
            self.display_seed_contact()
        else:
            log.debug("Seeding disabled")
            self.view.display_message("")
        log.debug("Seeding toggled, seeding is now {}".format(self.seeding))

    def display_seed_contact(self):
        log.debug("Displaying seed contact")
        next_label = self.selected_lead.next_contact_label()
        log.debug("Next label: {}".format(next_label))
        next_loc = self.selected_lead.next_contact_loc()
        log.debug("Next location: {}".format(next_loc))

        log.debug("Updating view with message...")
        msg = "Click on contact {}{} ({}, {})".format(self.selected_lead.label, next_label, *next_loc)
        self.view.display_message(msg)
        log.debug("View updated with message, display_seed_contact complete.")

    def set_lead_location(self, lead_location, lead_group):
        log.debug("Setting lead location to {} and group to {}".format(lead_location, lead_group))
        self.lead_location = lead_location
        self.lead_group = lead_group
        log.debug("Lead location set to {} and group to {}, set_lead_location done".format(lead_location, lead_group))

    def set_contact_label(self, label):
        log.debug("Setting contact label to {}".format(label))
        self.contact_label = label
        self.lead_group = 0
        log.debug("Contact label set to {}, set_contact_label done".format(label))

    def set_selected_lead(self, lead_name):
        log.debug("Setting selected lead to {}".format(lead_name))
        try:
            log.debug("Getting lead {}".format(lead_name))
            self.selected_lead = self.ct.get_lead(lead_name)
            log.debug("Updating lead dimensions in contact panel...")
            dims = self.selected_lead.dimensions
            log.debug("Lead dimensions: {}".format(dims))
            self.view.contact_panel.update_lead_dims(*dims)
            log.debug("Lead dimensions updated")
        except KeyError:
            log.error("Lead {} does not exist".format(lead_name))
        self.select_next_contact_label()
        log.debug("Selected lead set to {}, set_selected_lead done".format(lead_name))

    def toggle_RAS_axes(self,state):
        log.debug("Toggling RAS axes")
        self.view.toggle_RAS()

    def prompt_for_ct(self):
        """
        Callback for "Load Scan" button. See :load_ct:
        :return:
        """
        log.debug("Prompting for CT")
        (file_, filter_) = QFileDialog().getOpenFileName(None, 'Select Scan', '.', '(*)')
        if file_:
            log.debug("Loading CT from file {}".format(file_))
            self.load_ct(filename=file_)
            self.view.task_bar.define_leads_button.setEnabled(True)
            self.view.task_bar.save_button.setEnabled(True)
            self.view.task_bar.load_coord_button.setEnabled(True)
            self.view.task_bar.load_gridmap_file.setEnabled(True)
            self.view.task_bar.switch_coordinate_system.setEnabled(True)


    def load_ct(self, filename):
        """
        Loads a CT file and updates the view.
        :param filename: The name of the CT file.
        :return:
        """
        log.debug("Loading CT from file {}".format(filename))
        self.ct = CT(self.config)
        log.debug("Loading CT...")
        self.ct.load(filename,self.config['ct_threshold'])
        log.debug("CT loaded, updating view...")
        self.view.slice_view.set_label(filename)
        self.view.contact_panel.update_contacts()
        self.view.contact_panel.setEnabled(True)
        log.debug("View updated, adding _ct, _leads and _selected clouds")
        log.debug("Adding _ct cloud...")
        self.view.add_cloud(self.ct, '_ct', callback=self.select_coordinate)
        log.debug("Adding _leads cloud...")
        self.view.add_cloud(self.ct, '_leads')
        log.debug("Adding _selected cloud...")
        self.view.add_cloud(self.ct, '_selected')
        log.debug("Clouds added, updating slices...")
        self.view.add_RAS(self.ct)
        self.view.set_slice_scan(self.ct.data)
        log.debug("Slices updated, load_ct done.")

    def exec_(self):
        log.debug("Running application")
        self.app.exec()

    def assign_callbacks(self):
        log.debug("Assigning callbacks")
        self.view.task_bar.load_scan_button.clicked.connect(self.prompt_for_ct)
        self.view.task_bar.define_leads_button.clicked.connect(self.define_leads)
        self.view.task_bar.save_button.clicked.connect(self.save_coordinates)
        self.view.task_bar.load_coord_button.clicked.connect(self.load_coordinates)
        self.view.task_bar.load_gridmap_file.clicked.connect(self.load_gridmap_file)
        self.view.task_bar.switch_coordinate_system.clicked.connect(self.switch_coordinate_system)
        self.view.task_bar.load_mri_button.clicked.connect(self.prompt_for_mri)
        self.view.task_bar.mri_opacity.valueChanged.connect(self.update_mri_opacity)
        self.view.task_bar.translate_coords_button.clicked.connect(self.open_translate_coords)

    def open_translate_coords(self):
        """Open the coordinate translation popup window"""
        log.debug("Opening Translate Coordinates window")
        self.translate_window = TranslateCoordinatesWidget(self)
        self.translate_window.show()

    def switch_coordinate_system(self):
        self.ct.switch_coordinate_system()
        # Toggle a redraw of the CT, leads
        self.view.update_clouds()
        # Redraw the RAS axes with the update method
        self.view.switch_RAS_LAS()
    
    def assign_shortcuts(self):
        """
        Constructs keyboard shortcuts and assigns them to methods
        :return:
        """
        log.debug("Assigning shortcuts")
        QShortcut(QKeySequence('S'),self.view).activated.connect(self.add_selection)
        QShortcut(QKeySequence('Ctrl+O'),self.view).activated.connect(self.prompt_for_ct)
        QShortcut(QKeySequence('Ctrl+Shift+O'),self.view).activated.connect(self.load_coordinates)
        QShortcut(QKeySequence('Ctrl+D'),self.view).activated.connect(self.define_leads)
        QShortcut(QKeySequence('Ctrl+S'),self.view).activated.connect(self.save_coordinates)

    def save_coordinates(self):
        """
        Callback to save the localized coordinates in only JSON or text format
        :return:
        """
        log.debug("Saving coordinates")
        file,file_filter = QFileDialog().getSaveFileName(None,'Save as:',os.path.join(os.getcwd(),'voxel_coordinates.txt'),
                                                            'JSON (*.json);;TXT (*.txt)','JSON (*.json)')
        if file:
            log.debug("Saving to file {}".format(file))
            self.ct.saveas(file,os.path.splitext(file)[-1],self.view.task_bar.bipolar_box.isChecked())
            log.debug("Saved to file {}".format(file))
        log.debug("Save coordinates done.")

    def load_coordinates(self):
        """Load coordinates from txt/vox_mom file"""
        file_path, _ = QFileDialog().getOpenFileName(None, 'Load Coordinates', '.', '(*.txt *.vox_mom *.json)')
    
        if not file_path:
            return
        
        log.debug(f"Loading coordinates from {file_path}")
    
        try:
            if file_path.endswith('.json'):
                self.ct.from_json(file_path)
                success = True
            else:  # txt or vox_mom
                success = self.ct.from_vox_mom(file_path)
            
            if success:
                # Update UI elements
                self.view.update_clouds()
                self.view.contact_panel.update_contacts()
                log.info(f"Successfully loaded coordinates from {file_path}")
            
                # Enable save button
                self.view.task_bar.save_button.setEnabled(True)
            else:
                QMessageBox.warning(None, 'Loading Error', 
                    'No valid contacts were found in the coordinate file.\n'
                    'Check that the coordinates match the current CT scan.')
            
        except Exception as e:
            log.error(f"Failed to load coordinates: {str(e)}")
            QMessageBox.warning(None, 'Loading Error', 
                f'Failed to load coordinates: {str(e)}')

    def load_gridmap_file(self):
        log.debug("Loading gridmap file")
        (file, filter) = QFileDialog().getOpenFileName(None, 'Select gridmap file', '.', '(*)')
        if file:
            log.debug("Loading from file {}".format(file))
            self.ct.load_gridmap(file)
            log.debug("Loaded from file {}".format(file))
            log.debug("Updating view, and adding _leads cloud...")
            self.view.update_cloud('_leads')
            log.debug("_leads clouds updated, updating contact panel...")
            self.view.contact_panel.update_contacts()
            log.debug("Contact panel updated, load_gridmap_file done.")

    def define_leads(self):
        """
        Callback for "Define Leads" button
        :return:
        """
        log.debug("Defining leads")
        self.lead_window = QMainWindow()
        log.debug("Creating LeadDefinitionWidget")
        lead_widget = LeadDefinitionWidget(self, self.config, self.view)
        log.debug("Setting leads")
        lead_widget.set_leads(self.ct.get_leads())
        log.debug("Setting central widget")
        self.lead_window.setCentralWidget(lead_widget)
        self.lead_window.show()
        self.lead_window.resize(200, lead_widget.height())

    def select_coordinate(self, coordinate, do_center=True, allow_seed=True):
        """
        Callback for interacting with CT window.
        When a point in the screen is clicked, highlights the points near the selected point.
        If seeding is enabled, mark the highlighted points as current contact and seed as many additional contacts as possible.
        :param coordinate: The selected point in voxel space
        :param do_center: If true, tteratively select the center of the current selection, to better estimate the center of the contact.
        :param allow_seed: ???
        :return:
        """
        log.debug("select_coordinate: Selecting near coordinate {}".format(coordinate))
        self.clicked_coordinate = coordinate
        self.selected_coordinate = coordinate
        radius = self.selected_lead.radius if not self.selected_lead is None else 5
        log.debug("Selecting points near coordinate {} with radius {}".format(coordinate, radius))
        
        # Debug: Check if we have any points in our data
        if hasattr(self.ct, '_points') and self.ct._points is not None:
            all_coords = self.ct._points.get_coordinates()
            log.debug(f"select_coordinate: CT has {len(all_coords)} total points")
            log.debug(f"select_coordinate: CT coordinate range: min={np.min(all_coords, axis=0)}, max={np.max(all_coords, axis=0)}")
        else:
            log.warning("select_coordinate: CT points not available")
        
        # Try to select points near the coordinate
        try:
            self.ct.select_points_near(coordinate, radius)
            
            # Check if selection was successful
            if hasattr(self.ct, '_selection') and self.ct._selection is not None:
                selected_coords = self.ct._selection.coordinates()
                log.debug(f"select_coordinate: Selected {len(selected_coords)} points")
                if len(selected_coords) == 0:
                    log.warning(f"select_coordinate: No points found within radius {radius} of coordinate {coordinate}")
                    # Try with a larger radius
                    larger_radius = radius * 3
                    log.debug(f"select_coordinate: Trying with larger radius {larger_radius}")
                    self.ct.select_points_near(coordinate, larger_radius)
                    selected_coords = self.ct._selection.coordinates()
                    log.debug(f"select_coordinate: With larger radius, selected {len(selected_coords)} points")
            else:
                log.warning("select_coordinate: CT selection not available")
        except Exception as e:
            log.error(f"select_coordinate: Error selecting points: {e}")
            import traceback
            log.error(f"select_coordinate: Traceback: {traceback.format_exc()}")
        
        if do_center:
            log.debug("Centering selection")
            self.center_selection(self.config['selection_iterations'], radius)
        log.debug("Updating view...")
        panel = self.view.contact_panel
        for i, (_,contact) in enumerate(panel.contacts):
            if self.clicked_coordinate in contact:
                log.debug("Setting current row in contact list to {}".format(i))
                panel.contact_list.setCurrentRow(i)
                break
        else:
            log.debug("No contact found")
            panel.contact_list.setCurrentRow(panel.contact_list.currentRow(),QItemSelectionModel.SelectionFlag.Deselect)

        if not np.isnan(self.selected_coordinate).all():
            if self.seeding and allow_seed:
                log.debug("Seeding from coordinate {}".format(self.selected_coordinate))
                log.info("Seeding from coordinate {}".format(self.selected_coordinate))
                self.selected_lead.seed_next_contact(self.selected_coordinate)
                log.debug("Seeding done, updating view...")
                self.ct.clear_selection()
                log.debug("Clearing selection")
                log.debug("Updating view...")
                self.selected_coordinate = np.zeros((3,))
                log.debug
                self.view.update_cloud('_leads')
                self.select_next_contact_label()
                self.view.contact_panel.set_chosen_leads(self.ct.get_leads())
                self.display_seed_contact()
            else:
                self.view.update_ras(self.selected_coordinate)
                log.info("Selected coordinate {}".format(self.selected_coordinate))
        else:
            log.info("No coordinate selected")
        self.view.update_cloud('_selected')
        self.view.update_slices(self.selected_coordinate)

    def center_selection(self, iterations, radius):
        for _ in range(iterations):
            self.selected_coordinate = self.ct.selection_center()
            self.ct.select_points_near(self.selected_coordinate, radius)

    def confirm(self, label):
        reply = QMessageBox.question(None, 'Confirmation', label,
                                           QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    def add_selection(self):
        """
        Callback for "Submit" button on lead panel
        Adds selected pixels as new contact
        :return:
        """
        lead = self.selected_lead
        lead_label = lead.label
        contact_label = self.contact_label
        lead_location = self.lead_location[:]
        lead_group = self.lead_group

        if not self.ct.contact_exists(lead_label, contact_label) and \
                self.ct.lead_location_exists(lead_label, lead_location, lead_group):
            if not self.confirm("Lead location {} already exists. "
                                "Are you sure you want to duplicate?".format(lead_location)):
                return
        if self.config['zero_index_lead']:
            offset = 1
        else:
            offset = 0

        if lead_location[0] + offset > lead.dimensions[0] or \
                                lead_location[1] + offset > lead.dimensions[1]:
            if not self.confirm("Dimensions {} are outside of lead dimensions {}. "
                                "Are you sure you want to continue?".format(lead_location, lead.dimensions)):
                return

        try:
            self.ct.add_selection_to_lead(lead_label, contact_label, lead_location, self.lead_group)
            self.view.contact_panel.set_chosen_leads(self.ct.get_leads())
            self.ct.clear_selection()
            self.view.update_cloud('_leads')
            self.view.update_cloud('_selected')

            self.select_next_contact_label()
        except ValueError as e:
            # Handle case where no valid selection was made
            QMessageBox.warning(None, "Error adding selection", 
                      f"Cannot add selection to lead: {str(e)}\n\n"
                      f"Please make sure you have:\n"
                      f"1. Right-clicked on a point in the 3D view\n"
                      f"2. Made a valid selection near electrode contacts\n"
                      f"3. The selection is not empty")
            log.error(f"Failed to add selection to lead {lead_label}: {e}")

    def select_next_contact_label(self):
        lead = self.selected_lead

        self.contact_label = lead.next_contact_label()
        self.lead_location = lead.next_contact_loc()

        self.view.update_lead_location(*self.lead_location)
        self.view.update_contact_label(self.contact_label)

    def set_leads(self, labels, lead_types, dimensions, radii, spacings,micros=None):
        self.ct.set_leads(labels, lead_types, dimensions, radii, spacings,micros)
        leads = self.ct.get_leads()
        panel_labels = ['%s (%s x %s)' % (k, v.dimensions[0], v.dimensions[1]) for (k, v) in leads.items()]
        self.view.contact_panel.set_lead_labels(panel_labels)
        self.view.contact_panel.update_contacts()

    def delete_contact(self, lead_label, contact_label):
        try:
            self.ct.get_lead(lead_label).remove_contact(contact_label)
        except KeyError:
            pass
        self.view.contact_panel.set_chosen_leads(self.ct.get_leads())
        self.view.update_cloud('_leads')
        
    def prompt_for_mri(self):
        """Handler for Load MRI button"""
        log.debug("Prompting for MRI")
        mri_dir = QFileDialog().getExistingDirectory(None, 'Select Freesurfer MRI Directory')
        
        if mri_dir:
            aparc_file = os.path.join(mri_dir, 'mri/aparc+aseg.mgz')
            if os.path.exists(aparc_file):
                self.load_mri(aparc_file)
            else:
                QMessageBox.warning(None, 'Error', 
                    'Could not find aparc+aseg.mgz in selected directory')
                
    def load_mri(self, filename):
        """Load MRI data and display"""
        try:
            import nibabel as nib
            self.mri_filename = filename
            self.mri = nib.load(filename)
            
            # Register MRI to CT space
            # This would require implementation of registration logic
            registered_mri = self.register_to_ct(self.mri)
            
            # Add MRI visualization
            self.view.add_cloud(registered_mri, '_mri')
            
            # Enable opacity slider
            self.view.task_bar.mri_opacity.setEnabled(True)
            
            log.debug(f"Loaded MRI from {filename}")
            
        except Exception as e:
            log.error(f"Failed to load MRI: {str(e)}")
            QMessageBox.warning(None, 'Error', f'Failed to load MRI: {str(e)}')
            
    def register_to_ct(self, mri_img):
        """
        Register MRI to CT space using transformation matrices
        This is a placeholder - actual implementation would need proper registration
        """
        # Implementation needed for:
        # 1. Extract transformation matrices from CT and MRI
        # 2. Compute registration transform
        # 3. Apply transform to MRI data
        # 4. Return registered data
        pass

    def update_mri_opacity(self, value):
        """Update MRI visualization opacity"""
        if '_mri' in self.view.cloud_widget.viewer.clouds:
            opacity = value / 100.0
            self.view.cloud_widget.viewer.clouds['_mri'].set_opacity(opacity)


class PylocWidget(QWidget):
    def __init__(self, controller, config, parent=None):
        """
        The widget controlled by PylocController
        :param controller:
        :param config:
        :param parent:
        """
        QWidget.__init__(self, parent)
        self.controller = controller
        self.cloud_widget = CloudWidget(self, config)
        self.task_bar = TaskBarLayout()
        self.slice_view = SliceViewWidget(self)
        self.contact_panel = ContactPanelWidget(controller, config, self)
        self.contact_panel.setEnabled(False)
        self.threshold_panel = ThresholdWidget(controller=controller, config=config, parent=self)

        layout = QVBoxLayout(self)
        splitter = QSplitter()
        splitter.addWidget(self.contact_panel)
        splitter.addWidget(self.cloud_widget)
        splitter.addWidget(self.slice_view)
        splitter.setSizes([50,400,200])

        layout.addWidget(self.threshold_panel)
        layout.addWidget(splitter)
        layout.addLayout(self.task_bar)

    def clear(self):
        pass

    def display_message(self, msg):
        self.cloud_widget.display_message(msg)

    def update_cloud(self, label):
        self.cloud_widget.update_cloud(label)

    def update_clouds(self):
        self.cloud_widget.viewer.update_all()

    def update_slices(self, coordinates):
        self.slice_view.set_coordinate(coordinates)
        self.slice_view.update_slices()

    def plot_cloud(self,label):
        self.cloud_widget.plot_cloud(label)

    def add_cloud(self, ct, label, callback=None):
        log.debug("PylocWidget.add_cloud: Adding cloud {} to view".format(label))
        self.cloud_widget.add_cloud(ct, label, callback)

    def add_RAS(self,ct,callback=None):
        self.cloud_widget.add_RAS(ct,callback)

    def switch_RAS_LAS(self):
        self.cloud_widget.switch_RAS_LAS()

    def toggle_RAS(self):
        self.cloud_widget.toggle_RAS()

    def remove_cloud(self, label):
        self.cloud_widget.remove_cloud(label)

    def set_slice_scan(self, scan):
        self.slice_view.set_image(scan)

    def update_ras(self, coordinate):
        self.contact_panel.display_coordinate(coordinate)

    def update_contact_label(self, contact_label):
        self.contact_panel.set_contact_label(contact_label)

    def update_lead_location(self, x, y):
        self.contact_panel.set_lead_location(x, y)

    def closeEvent(self, event):
        """Save state before closing"""
        if self.task_bar.auto_save_checkbox.isChecked():
            self.controller.auto_save_state()
        super().closeEvent(event)

class NoScrollComboBox(QComboBox):
    """
    Subclass of QComboBox that doesn't interact with the scroll wheel.
    """
    def __init__(self,*args,**kwargs):
        super(NoScrollComboBox, self).__init__(*args,**kwargs)
        # Don't want to receive focus via scroll wheel
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, QWheelEvent):
        """
        No behavior on wheel events
        :param QWheelEvent:
        :return:
        """
        QWheelEvent.accept()
        return

class ContactPanelWidget(QWidget):
    def __init__(self, controller, config, parent=None):
        """
        Panel that displays and interacts with localized contacts
        :param controller: The PylocControl for the app
        :param config: The loaded config dict for the app
        :param parent: A parent widget
        """
        super(ContactPanelWidget, self).__init__(parent)
        self.config = config
        self.controller = controller
        self.view = parent  # Store reference to the main view

        layout = QVBoxLayout(self)

        lead_layout = QHBoxLayout()
        layout.addLayout(lead_layout)

        self.labels = OrderedDict()
        self.label_dropdown = NoScrollComboBox()
        self.label_dropdown.setMinimumWidth(150)
        self.label_dropdown.setMaximumWidth(200)
        add_labeled_widget(lead_layout,
                                "Label :", self.label_dropdown)
        self.contact_name = QLineEdit()
        lead_layout.addWidget(self.contact_name)

        loc_layout = QHBoxLayout()
        layout.addLayout(loc_layout)

        self.x_lead_loc = QLineEdit()
        self.x_loc_max = QLabel('')
        add_labeled_widget(loc_layout,
                                "Lead   x:", self.x_lead_loc,self.x_loc_max)

        self.y_lead_loc = QLineEdit()
        self.y_loc_max  = QLabel('')
        add_labeled_widget(loc_layout,
                                " y:", self.y_lead_loc,self.y_loc_max)

        self.lead_group = QLineEdit("0")
        add_labeled_widget(loc_layout,
                                " group:", self.lead_group)

        vox_layout = QHBoxLayout()
        layout.addLayout(vox_layout)

        self.r_voxel = QLineEdit()
        add_labeled_widget(vox_layout,
                                "R:", self.r_voxel)
        self.a_voxel = QLineEdit()
        add_labeled_widget(vox_layout,
                                "A:", self.a_voxel)
        self.s_voxel = QLineEdit()
        add_labeled_widget(vox_layout,
                                "S:", self.s_voxel)

        self.axes_checkbox = QCheckBox("Show RAS Tags")
        self.axes_checkbox.setChecked(True)
        vox_layout.addWidget(self.axes_checkbox)

        self.submit_button = QPushButton("Submit")

        layout.addWidget(self.submit_button)

        contact_label = QLabel("Contacts:")
        layout.addWidget(contact_label)

        self.contacts = []
        self.contact_list = QListWidget()
        self.contact_list.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        layout.addWidget(self.contact_list)

        self.interpolate_button = QPushButton("Interpolate")
        layout.addWidget(self.interpolate_button)

        self.seed_button = QPushButton("Seeding")
        self.seed_button.setCheckable(True)
        layout.addWidget(self.seed_button)

        self.micro_button = QPushButton("Add Micro-Contacts")
        layout.addWidget(self.micro_button)

        self.assign_callbacks()

    def display_coordinate(self, coordinate):
        self.r_voxel.setText("%.1f" % coordinate[0])
        self.a_voxel.setText("%.1f" % coordinate[1])
        self.s_voxel.setText("%.1f" % coordinate[2])

    def assign_callbacks(self):
        self.label_dropdown.currentIndexChanged.connect(self.lead_changed)
        self.contact_name.textChanged.connect(self.contact_changed)
        self.submit_button.clicked.connect(self.submit_pressed)
        self.x_lead_loc.textChanged.connect(self.lead_location_changed)
        self.y_lead_loc.textChanged.connect(self.lead_location_changed)
        self.lead_group.textChanged.connect(self.lead_location_changed)
        self.interpolate_button.clicked.connect(self.controller.interpolate_selected_lead)
        self.contact_list.currentItemChanged.connect(self.chosen_lead_selected)
        self.seed_button.clicked.connect(self.controller.toggle_seeding)
        self.micro_button.clicked.connect(self.controller.add_micro_contacts)
        self.axes_checkbox.stateChanged.connect(self.controller.toggle_RAS_axes)

    LEAD_LOC_REGEX = r'\((\d+\.?\d*),\s?(\d+\.?\d*),\s?(\d+\.?\d*)\)'

    def keyPressEvent(self, event):
        super(ContactPanelWidget, self).keyPressEvent(event)
        if event.key() == Qt.Key.Key_Delete:
            indices = self.contact_list.selectedIndexes()
            items  = [self.contacts[i.row()] for i in indices ]
            for (lead,contact) in items:
                try:
                    log.debug("Deleting contact {}{}".format(lead.label, contact.label))
                    self.controller.delete_contact(lead.label, contact.label)
                except Exception as e:
                    log.error("Could not delete contact: {}".format(e))
            self.update_contacts()

    def chosen_lead_selected(self):
        current_index = self.contact_list.currentIndex()
        if current_index.row() < 0 or current_index.row() >= len(self.contacts):
            return
            
        _, current_contact = self.contacts[current_index.row()]
        log.debug("Selecting contact {}".format(current_contact.label))
        
        # Highlight the selected contact
        if hasattr(self.view, 'cloud_widget') and hasattr(self.view.cloud_widget, 'viewer'):
            contact_coordinates = [current_contact.center]
            log.debug(f"Highlighting contact at coordinates: {contact_coordinates}")
            self.view.cloud_widget.viewer.highlight_contacts(contact_coordinates)
        
        # Also select the coordinate (existing behavior)
        self.controller.select_coordinate(current_contact.center, False, False)

    def set_contact_label(self, label):
        self.contact_name.setText(label)

    def set_lead_location(self, x, y):
        self.x_lead_loc.setText(str(x))
        self.y_lead_loc.setText(str(y))

    def update_lead_dims(self,x,y):
        self.x_loc_max.setText('/%s'%x)
        self.y_loc_max.setText('/%s'%y)

    def lead_location_changed(self):
        x = self.find_digit(self.x_lead_loc.text())
        self.x_lead_loc.setText(x)
        y = self.find_digit(self.y_lead_loc.text())
        self.y_lead_loc.setText(y)
        group = self.find_digit(self.lead_group.text())
        self.lead_group.setText(group)

        if len(x) > 0 and len(y) > 0 and len(group) > 0:
            self.controller.set_lead_location([int(x), int(y)], int(group))

    @staticmethod
    def find_digit(label):
        return re.sub(r"[^\d]", "", str(label))

    def lead_changed(self):
        lead_txt = self.label_dropdown.currentText()
        if(lead_txt == ''):
            return # No leads to select
        self.controller.set_selected_lead(lead_txt.split()[0])
        self.lead_group.setText("0")
        self.lead_location_changed()

    def contact_changed(self):
        self.controller.set_contact_label(self.contact_name.text())

    def submit_pressed(self):
        self.controller.add_selection()

    def set_chosen_leads(self, leads):
        self.contact_list.clear()
        self.contacts = []
        for lead_name in sorted(leads.keys()):
            lead = leads[lead_name]
            for contact_name in sorted(lead.contacts.keys(), key=lambda x: int(''.join(re.findall(r'\d+', x)))):
                contact = lead.contacts[contact_name]
                self.add_contact(lead, contact)

    def add_contact(self, lead, contact):
        self.contact_list.addItem(
            QListWidgetItem(self.config['lead_display'].format(lead=lead, contact=contact).strip())
        )
        self.contacts.append((lead, contact))

    def update_contacts(self):
        """
        Aligns self.contact_list with self.controller.ct._leads
        :return:
        """
        ct = self.controller.ct
        if ct is not None:
            leads = ct.get_leads()
            self.set_chosen_leads(leads)
            self.controller.view.update_cloud('_leads')
            labels = ['%s (%s x %s)'%(k,v.dimensions[0],v.dimensions[1]) for (k,v) in leads.items()]
            self.set_lead_labels(labels)

    def set_lead_labels(self, lead_labels):
        # Clear the dropdown, and disable the update callback here
        self.label_dropdown.clear()
        for lead_name in lead_labels:
            self.label_dropdown.addItem(lead_name)


class LeadDefinitionWidget(QWidget):
    instance = None

    def __init__(self, controller, config, parent=None):
        super(LeadDefinitionWidget, self).__init__(parent)
        self.config = config
        self.controller = controller

        # Subwidgets
        self.label_edit = QLineEdit()
        self.x_size_edit = QLineEdit()
        self.y_size_edit = QLineEdit()
        self.type_box = QComboBox()

        for label, electrode_type in config['lead_types'].items():
            if 'u' not in label:
                self.type_box.addItem("{}: {name}".format(label, **electrode_type))

        self.micro_box = QComboBox()
        for micro_lead_type in sorted(config['micros'].keys()):
            self.micro_box.addItem(micro_lead_type)

        self.submit_button = QPushButton("Submit")

        self.delete_button = QPushButton("Delete")
        self.close_button = QPushButton("Confirm")

        self.leads_list = QListWidget()

        self.add_callbacks()
        self.set_layout()
        self.set_tab_order()
        self.set_shortcuts()
        self._leads = OrderedDict()

    def set_layout(self):
        layout = QVBoxLayout(self)
        add_labeled_widget(layout,
                                "Lead Name: ", self.label_edit)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Dimensions: "))
        add_labeled_widget(size_layout, "x:", self.x_size_edit)
        add_labeled_widget(size_layout, "y:", self.y_size_edit)

        layout.addLayout(size_layout)

        add_labeled_widget(layout, "Type: ", self.type_box)

        add_labeled_widget(layout,"Micro-contacts: ",self.micro_box)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.leads_list)

        bottom_layout = QHBoxLayout()

        bottom_layout.addWidget(self.delete_button)
        bottom_layout.addWidget(self.close_button)
        layout.addLayout(bottom_layout)


    def add_callbacks(self):
        self.submit_button.clicked.connect(self.add_current_lead)
        self.close_button.clicked.connect(self.finish)
        self.delete_button.clicked.connect(self.delete_lead)

    def set_tab_order(self):
        self.setTabOrder(self.micro_box,self.submit_button)
        self.setTabOrder(self.submit_button,self.leads_list)
        self.setTabOrder(self.leads_list,self.delete_button)
        self.setTabOrder(self.delete_button,self.close_button)

    def set_shortcuts(self):
        submit_shortcut = QShortcut(QKeySequence('S'),self)
        submit_shortcut.activated.connect(self.add_current_lead)

        confirm_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return),self)
        confirm_shortcut.activated.connect(self.finish)
        confirm_shortcut = QShortcut(QKeySequence( Qt.Key.Key_Enter),self)
        confirm_shortcut.activated.connect(self.finish)

        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete),self)
        delete_shortcut.activated.connect(self.delete_lead)

        focus_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape),self)
        focus_shortcut.activated.connect(self.setFocus)


    @classmethod
    def launch(cls, controller, config, parent=None):
        window = QMainWindow()
        widget = cls(controller, config, parent)
        window.setCentralWidget(widget)
        window.show()
        window.resize(200, cls.instance.height())
        return window

    def finish(self):
        leads = self._leads.values()
        labels = [lead['label'] for lead in leads]
        types = [lead['type'] for lead in leads]
        dimensions = [(lead['x'], lead['y']) for lead in leads]
        spacings = [self.config['lead_types'][lead_type]['spacing'] for lead_type in types]
        radii = [self.config['lead_types'][lead_type]['radius'] for lead_type in types]
        micros = [self.config['micros'][str(l.get('micro',' None'))] for l in leads]
        self.controller.set_leads(labels, types, dimensions, radii, spacings,micros)
        self.close()
        self.controller.lead_window.close()

    def set_leads(self, leads):
        self._leads = {lead.label:
                       {"label": lead.label,
                        "x":lead.dimensions[0],
                        "y":lead.dimensions[1],
                        "type":lead.type_,
                        "micro":lead.micros['name']}
                      for lead in leads.values() }
        self.refresh()

    def refresh(self):
        self.leads_list.clear()
        for lead in self._leads.values():
            self.leads_list.addItem(
                QListWidgetItem(
                    "{label} ({x} x {y}, {type})".format(**lead)
                )
            )

    def add_current_lead(self):
        x_str = str(self.x_size_edit.text())
        y_str = str(self.y_size_edit.text())

        if not x_str.isdigit() or not y_str.isdigit():
            return

        type_str = self.type_box.currentText()
        label_str = str(self.label_edit.text())
        micro_str = self.micro_box.currentText()
        self._leads[label_str] = dict(
            label=label_str,
            x=int(x_str),
            y=int(y_str),
            type=type_str[0],
            micro=micro_str,
        )
        self.refresh()

    def delete_lead(self):
        lead = self.leads_list.currentItem()
        if lead is not None:
            label = lead.text().split()[0]
            log.debug('Removing lead %s'%label)
            del self._leads[label]
            self.refresh()

    @staticmethod
    def add_labeled_widget(layout, label, widget):
        sub_layout = QHBoxLayout()
        label_widget = QLabel(label)
        sub_layout.addWidget(label_widget)
        sub_layout.addWidget(widget)
        layout.addLayout(sub_layout)

class ThresholdWidget(QWidget):
    """
    Subwindow for changing the threshold
    """
    def __init__(self,controller,config,parent=None):
        super(ThresholdWidget, self).__init__(parent)

        self.controller = controller
        self.config = config
        
        self.set_threshold_button = QPushButton("Update")
        self.set_threshold_button.clicked.connect(self.update_pressed)
        self.threshold_selector = QDoubleSpinBox()
        self.threshold_selector.setSingleStep(0.5)
        self.threshold_selector.setValue(self.config['ct_threshold'])
        self.threshold_selector.valueChanged.connect(self.update_threshold_value)
        self.threshold_selector.setKeyboardTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1,1,1,1)
        add_labeled_widget(layout,'CT Threshold',self.threshold_selector,self.set_threshold_button)

        self.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)

    def update_pressed(self):
        if self.controller.ct:
            self.controller.ct.set_threshold(self.config['ct_threshold'])
            for label in ['_ct','_leads','_selected']:
                self.controller.view.update_cloud(label)

    def update_threshold_value(self,value):
        self.config['ct_threshold']= value



class TaskBarLayout(QHBoxLayout):
    def __init__(self, parent=None):
        super(TaskBarLayout, self).__init__(parent)
        self.load_scan_button = QPushButton("Load Scan")
        self.define_leads_button = QPushButton("Define Leads")
        self.define_leads_button.setEnabled(False)
        self.load_coord_button = QPushButton("Load Coordinates")
        self.load_coord_button.setEnabled(False)
        self.clean_button = QPushButton("Clean scan")
        self.save_button=QPushButton("Save as...")
        self.save_button.setEnabled(False)
        self.bipolar_box = QCheckBox("Include Bipolar Pairs")
        # Sets up the button to load a gridmap file.
        self.load_gridmap_file = QPushButton("Load Gridmap File")
        self.load_gridmap_file.setEnabled(False)
        self.switch_coordinate_system = QPushButton("Switch Coordinate System")
        self.switch_coordinate_system.setEnabled(False)

        save_layout = QVBoxLayout()
        save_layout.addWidget(self.save_button)
        save_layout.addWidget(self.bipolar_box)

        self.addWidget(self.load_scan_button)
        self.addWidget(self.define_leads_button)
        self.addWidget(self.load_coord_button)
        self.addLayout(save_layout)
        self.addWidget(self.clean_button)
        self.addWidget(self.load_gridmap_file)
        self.addWidget(self.switch_coordinate_system)

        self.auto_save_checkbox = QCheckBox("Enable Auto-save")
        self.auto_save_checkbox.setChecked(True)
        self.auto_save_checkbox.stateChanged.connect(self.toggle_autosave)
        
        save_layout.addWidget(self.auto_save_checkbox)
        
        # Add MRI loading button
        self.load_mri_button = QPushButton("Load MRI")
        self.load_mri_button.setEnabled(False)
        
        # Add opacity sliders
        self.mri_opacity = QSlider(Qt.Orientation.Horizontal)
        self.mri_opacity.setRange(0, 100)
        self.mri_opacity.setValue(50)
        self.mri_opacity.setEnabled(False)
        
        mri_layout = QVBoxLayout()
        mri_layout.addWidget(self.load_mri_button)
        mri_layout.addWidget(QLabel("MRI Opacity:"))
        mri_layout.addWidget(self.mri_opacity)
        
        # Add Translate Coordinates button
        self.translate_coords_button = QPushButton("Translate Coordinates")
        self.translate_coords_button.setEnabled(True)
        
        # Add to layout near the end
        self.addLayout(mri_layout)
        self.addWidget(self.translate_coords_button)

    def toggle_autosave(self, state):
        if state == Qt.Checked:
            self.parent().controller.autosave_timer.start()
        else:
            self.parent().controller.autosave_timer.stop()

class CloudWidget(QWidget):
    def __init__(self, controller, config, parent=None):
        super(CloudWidget, self).__init__(parent)
        self.config = config
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.viewer = CloudViewer(config)
        
        # Instead of using TraitsUI, directly embed the PyVista scene widget
        layout.addWidget(self.viewer.scene.scene)
        
        self.controller = controller

    def update_cloud(self, label):
        self.viewer.update_cloud(label)

    def add_cloud(self, ct, label, callback=None):
        log.debug("CloudWidget.add_cloud: Adding cloud {} to view".format(label))
        self.viewer.add_cloud(ct, label, callback)

    def add_RAS(self,ct,callback=None):
        self.viewer.add_RAS(ct,callback)

    def switch_RAS_LAS(self):
        self.viewer.switch_RAS_LAS()

    def toggle_RAS(self):
        RAS = self.viewer.RAS
        if (RAS._plots and all([x.visible for x in RAS._plots])):
            RAS.hide()
        else:
            RAS.show()
    
    def plot_cloud(self,label):
        self.viewer.plot_cloud(label)

    def unplot_cloud(self,label):
        self.viewer.unplot_cloud(label)

    def remove_cloud(self, label):
        self.viewer.remove_cloud(label)

    def display_message(self, msg):
        self.viewer.display_message(msg)

class CloudViewer(HasTraits):
    BACKGROUND_COLOR = (.1, .1, .1)

    # Class-level persistent color mapping to maintain lead colors across sessions
    _lead_color_assignments = {}
    _next_color_index = 0
    
    # Define distinct RGB colors for different electrode shanks/leads
    _lead_rgb_colors = [
        [1.0, 0.0, 0.0],    # Red
        [0.0, 0.8, 0.0],    # Green  
        [0.0, 0.0, 1.0],    # Blue
        [1.0, 0.8, 0.0],    # Yellow
        [1.0, 0.0, 1.0],    # Magenta
        [0.0, 0.8, 1.0],    # Cyan
        [1.0, 0.5, 0.0],    # Orange
        [0.6, 0.0, 1.0],    # Purple
        [0.0, 0.6, 0.0],    # Dark green
        [0.8, 0.8, 0.0],    # Olive
        [0.8, 0.4, 0.2],    # Brown
        [1.0, 0.6, 0.8],    # Pink
    ]

    scene = Instance(PyVistaSceneModel, ())

    def __init__(self, config):
        super(CloudViewer, self).__init__()
        self.config = config
        self.scene = PyVistaSceneModel()
        self.plotter = self.scene.plotter
        self.scene.set_background_color(self.BACKGROUND_COLOR)
        self.clouds = {}
        self.text_displayed = None
        self.RAS = None
        
        # Connect picking signal
        log.debug("CloudViewer.__init__: Connecting point picking signal...")
        self.scene.scene.point_picked.connect(self.on_point_picked)
        log.debug("CloudViewer.__init__: Point picking signal connected")

    @classmethod
    def get_lead_color(cls, lead_name):
        """Get a persistent color for a lead name. Once assigned, the color never changes."""
        if lead_name not in cls._lead_color_assignments:
            # Assign the next available color
            color_index = cls._next_color_index % len(cls._lead_rgb_colors)
            cls._lead_color_assignments[lead_name] = cls._lead_rgb_colors[color_index]
            cls._next_color_index += 1
            log.debug(f"CloudViewer.get_lead_color: Assigned color {color_index} to lead '{lead_name}': {cls._lead_rgb_colors[color_index]}")
        
        return cls._lead_color_assignments[lead_name]
    
    @classmethod
    def reset_color_assignments(cls):
        """Reset all color assignments (useful for new sessions)"""
        cls._lead_color_assignments.clear()
        cls._next_color_index = 0
        log.debug("CloudViewer.reset_color_assignments: All lead color assignments cleared")

    def on_point_picked(self, point):
        """Handle point picking events from PyVista"""
        log.debug(f"CloudViewer.on_point_picked: Point picked at {point}")
        
        # Convert to the callback format expected by the rest of the code
        class MockPicker:
            def __init__(self, point):
                self.pick_position = point
        picker = MockPicker(point)
        
        log.debug(f"CloudViewer.on_point_picked: Available clouds: {list(self.clouds.keys())}")
        
        # Prioritize the '_ct' cloud for picking (main interaction)
        if '_ct' in self.clouds and self.clouds['_ct'].contains(picker):
            log.debug("CloudViewer.on_point_picked: Delegating to '_ct' cloud callback")
            self.clouds['_ct'].callback(picker)
            return
        
        # Find which cloud contains this point and call its callback
        for label, cloud_view in self.clouds.items():
            if cloud_view.contains(picker):
                log.debug(f"CloudViewer.on_point_picked: Delegating to '{label}' cloud callback")
                cloud_view.callback(picker)
                break
        else:
            log.warning("CloudViewer.on_point_picked: No cloud found to handle the picked point")

    def update_cloud(self, label):
        if self.clouds and label in self.clouds:
            self.clouds[label].update()

    def plot_cloud(self,label):
        if label in self.clouds:
            self.clouds[label].plot()

    def unplot_cloud(self,label):
        if label in self.clouds:
            self.clouds[label].unplot()

    def add_cloud(self, ct, label, callback=None):
        log.debug("CloudViewer.add_cloud: Adding cloud {} to view".format(label))
        if label in self.clouds:
            log.debug("CloudViewer.add_cloud: Cloud {} already exists, removing...".format(label))
            self.remove_cloud(label)
        self.clouds[label] = CloudView(ct, label, self.config, self.scene.scene, callback)
        self.clouds[label].plot()

    def highlight_contacts(self, coordinates):
        """Highlight specific contacts by coordinates with enhanced visibility"""
        log.debug(f"CloudViewer.highlight_contacts: Highlighting {len(coordinates)} contacts")
        
        # Remove existing highlighted cloud if any
        if '_highlighted' in self.clouds:
            self.remove_cloud('_highlighted')
            
        if len(coordinates) > 0:
            # Create a temporary CT-like object for the highlighted points
            class HighlightedPoints:
                def __init__(self, coords):
                    self.coords = coords
                    
                def xyz(self, label):
                    if label == '_highlighted':
                        labels = ['_highlighted'] * len(self.coords)
                        x = [coord[0] for coord in self.coords]
                        y = [coord[1] for coord in self.coords]
                        z = [coord[2] for coord in self.coords]
                        return labels, x, y, z
                    return [], [], [], []
            
            highlighted_ct = HighlightedPoints(coordinates)
            self.clouds['_highlighted'] = CloudView(highlighted_ct, '_highlighted', self.config, self.scene.scene)
            
            # Override plot method to use enhanced visual properties for highlighting
            original_plot = self.clouds['_highlighted'].plot
            def enhanced_plot():
                labels, x, y, z = highlighted_ct.xyz('_highlighted')
                if len(x) == 0:
                    return
                    
                points = np.column_stack((x, y, z))
                # Bright white color for highlight
                colors = np.array([[1.0, 1.0, 1.0]] * len(points))
                
                log.debug(f"CloudView.enhanced_plot: Adding highlighted points")
                self.clouds['_highlighted']._plot = self.clouds['_highlighted'].scene.add_point_cloud(
                    points=points,
                    colors=colors,
                    name=self.clouds['_highlighted']._actor_name,
                    mode='cube',
                    opacity=1.0,
                    point_size=12,  # Larger size for visibility
                    constant_size=True,  # Keep size constant regardless of zoom
                )
                
            self.clouds['_highlighted'].plot = enhanced_plot
            self.clouds['_highlighted'].plot()
            
    def clear_highlights(self):
        """Clear all highlighted contacts"""
        if '_highlighted' in self.clouds:
            self.remove_cloud('_highlighted')

    def add_RAS(self,ct,callback=None):
        self.RAS = AxisView(ct,self.config,self.scene.scene,callback)
        self.RAS.plot()

    def switch_RAS_LAS(self):
        self.RAS.update()

    def remove_cloud(self, label):
        self.clouds[label].unplot()
        del self.clouds[label]

    def plot(self):
        # Point picking is already set up in __init__ via self.scene.scene.point_picked.connect()
        for view in self.clouds.values():
            view.plot()

    def update_all(self):
        self.scene.set_background_color(self.BACKGROUND_COLOR)
        for view in self.clouds.values():
            view.update()

    def display_message(self, msg):
        if self.text_displayed:
            self.scene.scene.remove_text('message')
        if msg:
            self.text_displayed = self.scene.scene.add_text(msg, position=(0.01, 0.95), name='message')
        else:
            self.text_displayed = None


class CloudView(object):
    def get_colormap(self, label):
        if label == '_ct':
            return self.config['colormaps']['ct']
        elif label == '_selected':
            return self.config['colormaps']['selected']
        elif label == '_highlighted':
            return 'Reds'  # Use red colormap for highlighting
        else:
            return 'Set1'  # Use categorical colormap for leads

    def __init__(self, ct, label, config, scene, callback=None):
        log.debug("CloudView.__init__: Setting ct")
        self.ct = ct
        log.debug("CloudView.__init__: Setting config")
        self.config = config
        log.debug("CloudView.__init__: Setting label")
        self.label = label
        log.debug("CloudView.__init__: Setting colormap")
        self.colormap = self.get_colormap(label)
        log.debug("CloudView.__init__: Setting callback")
        self._callback = callback if callback else lambda *_: None
        log.debug("CloudView.__init__: Setting scene")
        self.scene = scene
        log.debug("CloudView.__init__: Setting plot and glyph to None")
        self._plot = None
        self._actor_name = f"cloud_{label}"
        log.debug("CloudView.__init__: Done")

    def callback(self, picker):
        log.debug(f"CloudView.callback: Called for label '{self.label}' with pick_position {picker.pick_position}")
        if self._callback:
            log.debug(f"CloudView.callback: Calling callback function")
            return self._callback(np.array(picker.pick_position))
        else:
            log.warning(f"CloudView.callback: No callback function defined for '{self.label}'")

    def get_colors(self, labels, x, y, z):
        if len(labels) == 0:
            return []
            
        # Create color array (N x 3 for RGB)
        colors = np.zeros((len(labels), 3))
        min_y = float(min(y)) if len(y) > 0 else 0
        max_y = float(max(y)) if len(y) > 0 else 1
        
        # Get unique leads that need color assignment
        unique_leads = list(set([label for label in labels if label not in ['_ct', '_selected', '_highlighted']]))
        
        # Pre-assign colors for all unique leads to ensure consistency
        for lead_name in unique_leads:
            CloudViewer.get_lead_color(lead_name)
        
        log.debug(f"CloudView.get_colors: Current lead color assignments: {CloudViewer._lead_color_assignments}")
        
        for i, label in enumerate(labels):
            if label == '_ct':
                # State 1: Unselected CT points - light gray
                colors[i] = [0.7, 0.7, 0.7]
            elif label == '_selected':
                # State 1: Unselected electrodes - darker gray  
                colors[i] = [0.5, 0.5, 0.5]
            elif label == '_highlighted':
                # State 2: Highlighted electrode - bright white with glow effect
                colors[i] = [1.0, 1.0, 1.0]
            else:
                # State 3: Defined electrode shank - use persistent color assignment
                colors[i] = CloudViewer.get_lead_color(label)
                
        log.debug(f"CloudView.get_colors: Generated {len(colors)} RGB colors for label '{self.label}'")
        return colors

    def contains(self, picker):
        return True if self._plot else False  # and picker.pick_position in self.ct.xyz(self.label)

    def plot(self):
        labels, x, y, z = self.ct.xyz(self.label)
        
        # Debug: print information about the data
        log.debug(f"CloudView.plot: label={self.label}, labels={len(labels)}, x={len(x)}, y={len(y)}, z={len(z)}")
        
        # Check if we have any points to plot
        if len(x) == 0 or len(y) == 0 or len(z) == 0:
            log.warning(f"No points to plot for label '{self.label}' - skipping")
            return
        
        # Create points array
        points = np.column_stack((x, y, z))
        colors = self.get_colors(labels, x, y, z)
        
        log.debug(f"CloudView.plot: Created points array with shape {points.shape}")
        
        # For large datasets, use simple points instead of cubes for performance
        render_mode = 'cube'
        if points.shape[0] > 5000:  # Threshold for switching to points
            render_mode = 'points'
            log.debug(f"CloudView.plot: Large dataset ({points.shape[0]} points), using point mode for performance")
        
        # Add point cloud to PyVista scene
        log.debug(f"CloudView.plot: Adding point cloud with mode={render_mode} for {points.shape[0]} points...")
        self._plot = self.scene.add_point_cloud(
            points=points,
            colors=colors,
            name=self._actor_name,
            mode=render_mode,
            opacity=0.5,
            scale_factor=1,
            cmap=self.colormap,
            constant_size=True,  # Keep size constant regardless of zoom
            callback=self.callback,  # Pass callback for point picking
        )
        log.debug(f"CloudView.plot: Point cloud added successfully")

    def unplot(self):
        if self._plot:
            self.scene.remove_point_cloud(self._actor_name)
            self._plot = None
    '''
    def update(self):
        labels, x, y, z = self.ct.xyz(self.label)
        log.debug("Updating cloud {} with {} points".format(self.label, len(labels)))
        self._plot.mlab_source.reset(
            x=x, y=y, z=z, scalars=self.get_colors(labels, x, y, z))
    '''
    def update(self):
        labels, x, y, z = self.ct.xyz(self.label)
        log.debug("Updating cloud {} with {} points".format(self.label, len(labels)))
        
        # Check if we have any points to plot
        if len(x) == 0 or len(y) == 0 or len(z) == 0:
            log.warning(f"No points to update for label '{self.label}' - skipping")
            # Remove existing plot if any
            if self._plot:
                self.scene.remove_point_cloud(self._actor_name)
                self._plot = None
            return
        
        # Save camera position
        camera_position = self.scene.get_camera_position()
        
        # Remove old plot and create new one
        if self._plot:
            self.scene.remove_point_cloud(self._actor_name)
        
        # Create new plot with updated data
        points = np.column_stack((x, y, z))
        colors = self.get_colors(labels, x, y, z)
        
        self._plot = self.scene.add_point_cloud(
            points=points,
            colors=colors,
            name=self._actor_name,
            mode='cube',
            opacity=0.5,
            scale_factor=1,
            cmap=self.colormap,
            constant_size=True,  # Keep size constant regardless of zoom
        )
        
        # Restore camera position
        self.scene.set_camera_position(camera_position)
        self.scene.render()


class AxisView(CloudView):

    def __init__(self,ct,config,scene,callback=None):
        super(AxisView, self).__init__(ct,config=config,scene=scene,label='Axis',callback=callback)
        self.scale = 35
        self._plots = []
        self._text_actors = []

    def plot(self):
        coords = self.ct._points.coordinates
        center = np.array([0.5*(coords[:,i].max() + coords[:,i].min()) for i in range(3)])
        u,v,w,t = self.ct.affine.T
        max_dist = np.abs(coords-center).max()
        # axis = [1, 0 , 0] this refers to R and L labeling.
        # axis = [0, 1, 0] this refers to A and P labeling.
        # axis = [0, 0, 1] this refers to S and I labeling.
        try:
            name_pair_list = [['R','L'],['A','P'],['S','I']]
            if (self.ct.coordSystem == 'LAS'):
                # Swap the order of R and L
                name_pair_list[0] = ['L', 'R']
            # If any elements of u, v or w are less than 1e-4, treat them as 0.
            u[np.abs(u)<1e-4] = 0.0
            v[np.abs(v)<1e-4] = 0.0
            w[np.abs(w)<1e-4] = 0.0
            u = np.int32(np.sign(u))
            v = np.int32(np.sign(v))
            w = np.int32(np.sign(w))
            for i, axis in enumerate(zip((u,v,w))):
                # axis is a 3-tuple, find the index of the element which is closest to 1 (or -1)
                axis = axis[0] # tuple to list
                nonZero = np.nonzero(axis)
                # Assert if there are more than one non-zero element
                assert len(nonZero) == 1
                selectedAxis = int(nonZero[0][0])  # Fix indexing issue
                name_pair = name_pair_list[selectedAxis]
                for name in name_pair:
                    location  = center.copy()
                    if name is name_pair[0]:
                        loc = max_dist*1.25 * np.sign(axis[selectedAxis])
                        location[i] += loc
                    else:
                        loc = max_dist*1.25 * np.sign(axis[selectedAxis])
                        location[i] -= loc
                    
                    # Use PyVista text instead of mlab.text3d
                    text_name = f"axis_text_{name}_{i}"
                    text_actor = self.scene.add_text(
                        name, 
                        position=location, 
                        name=text_name
                    )
                    self._text_actors.append(text_name)
        except TypeError as e:
            log.error("Could not plot RAS axes: {}".format(e))
        except IndexError as e:
            log.error("Could not plot RAS axes: {}".format(e))
        except AssertionError as e:
            log.error("Could not plot RAS axes: {}".format(e))

    def contains(self, picker):
        return False

    def update(self):
        self.unplot()
        self.plot()
        return

    def hide(self):
        # PyVista doesn't have direct visibility control for text, so we'll remove/add
        pass

    def show(self):
        # PyVista doesn't have direct visibility control for text, so we'll remove/add  
        pass

    def unplot(self):
        # Remove text actors
        for text_name in self._text_actors:
            self.scene.remove_text(text_name)
        self._text_actors = []
        
        # Call parent unplot for any point clouds
        super().unplot()



if __name__ == '__main__':
    # controller = PylocControl(yaml.load(open(os.path.join(os.path.dirname(__file__) , "../config.yml"))))
    #controller = PylocControl()
    controller = PylocControl(yaml.load(open(os.path.join(os.path.dirname(__file__), "../config.yml")), Loader=yaml.SafeLoader))

    # controller.load_ct("../T01_R1248P_CT.nii.gz")
    # controller.load_ct('/Volumes/rhino_mount/data10/RAM/subjects/R1226D/tal/images/combined/R1226D_CT_combined.nii.gz')
    controller.load_ct('/Users/iped/PycharmProjects/voxTool/R1226D_CT_combined.nii.gz')
    controller.set_leads(
        #    ["sA", "sB", "dA", "dB"], ["S", "S", "D", "D"], ([[6, 1]] * 2) + ([[8, 1]] * 2), ([5] * 2) + ([5] * 2), [10] * 4
        ("G45", "G48"), ("G", "G"), ([4, 5], [4, 8]), [5, 5], [10, 10]
        # ["dA", "dB", "dC"], ["D", "D", "G"], [[8, 1], [8, 1], [4, 4]], [5, 10, 10], [10, 20, 20]
    )
    controller.exec_()

if __name__ == 'x__main__':
    app = QApplication.instance()
    x = LeadDefinitionWidget(None, yaml.load(open(os.path.join(os.path.dirname(__file__), "../model/config.yml")), Loader=yaml.SafeLoader))
    x.show()
    window = QMainWindow()
    window.setCentralWidget(x)
    window.show()
    app.exec()

class TranslateCoordinatesWidget(QWidget):
    def __init__(self, controller, parent=None):
        super(TranslateCoordinatesWidget, self).__init__(parent)
        self.controller = controller
        self.setWindowTitle("Translate Coordinates")
        
        # CT scan paths
        self.ref_ct_path = None
        self.floating_ct_path = None
        self.coords_file_path = None
        self.registration_transform = None
        
        # Create UI elements
        self.create_ui()
        self.setup_callbacks()
        
        # Set initial states
        self.update_ui_state()
        
    def create_ui(self):
        layout = QVBoxLayout(self)
        
        # Reference CT section
        ref_group = QGroupBox("Reference CT")
        ref_layout = QVBoxLayout(ref_group)
        
        self.ref_ct_button = QPushButton("Load Reference CT")
        self.ref_ct_label = QLabel("No reference CT loaded")
        
        ref_layout.addWidget(self.ref_ct_button)
        ref_layout.addWidget(self.ref_ct_label)
        
        # Floating CT section
        float_group = QGroupBox("Floating CT")
        float_layout = QVBoxLayout(float_group)
        
        self.floating_ct_button = QPushButton("Load Floating CT")
        self.floating_ct_label = QLabel("No floating CT loaded")
        
        float_layout.addWidget(self.floating_ct_button)
        float_layout.addWidget(self.floating_ct_label)
        
        # Registration section
        reg_group = QGroupBox("Registration")
        reg_layout = QVBoxLayout(reg_group)
        
        self.register_button = QPushButton("Register CTs")
        self.register_button.setEnabled(False)
        self.register_status = QLabel("Not registered")
        
        reg_layout.addWidget(self.register_button)
        reg_layout.addWidget(self.register_status)
        
        # Coordinates section
        coords_group = QGroupBox("Coordinates")
        coords_layout = QVBoxLayout(coords_group)
        
        self.load_coords_button = QPushButton("Load Coordinates")
        self.load_coords_button.setEnabled(False)
        self.coords_label = QLabel("No coordinates loaded")
        
        self.transform_coords_button = QPushButton("Transform Coordinates")
        self.transform_coords_button.setEnabled(False)
        
        coords_layout.addWidget(self.load_coords_button)
        coords_layout.addWidget(self.coords_label)
        coords_layout.addWidget(self.transform_coords_button)
        
        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Add sections to main layout
        layout.addWidget(ref_group)
        layout.addWidget(float_group)
        layout.addWidget(reg_group)
        layout.addWidget(coords_group)
        layout.addWidget(self.progress_bar)
        
        # Size the window appropriately
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        
    def setup_callbacks(self):
        self.ref_ct_button.clicked.connect(self.load_reference_ct)
        self.floating_ct_button.clicked.connect(self.load_floating_ct)
        self.register_button.clicked.connect(self.register_ct_scans)
        self.load_coords_button.clicked.connect(self.load_coordinates)
        self.transform_coords_button.clicked.connect(self.transform_coordinates)
        
    def update_ui_state(self):
        # Enable register button if both CTs are loaded
        has_ref = self.ref_ct_path is not None
        has_float = self.floating_ct_path is not None
        is_registered = self.registration_transform is not None
        has_coords = self.coords_file_path is not None
        
        self.register_button.setEnabled(has_ref and has_float)
        self.load_coords_button.setEnabled(has_float)
        self.transform_coords_button.setEnabled(is_registered and has_coords)
        
    def load_reference_ct(self):
        file_path, _ = QFileDialog().getOpenFileName(self, 'Select Reference CT Scan', '.', '(*)')
        if file_path:
            log.debug(f"Loading reference CT from {file_path}")
            self.ref_ct_path = file_path
            self.ref_ct_label.setText(f"Loaded: {os.path.basename(file_path)}")
            
            # Create a CT object from the file
            self.ref_ct = CT(self.controller.config)
            self.ref_ct.load(file_path, self.controller.config['ct_threshold'])
            
            self.update_ui_state()
            
    def load_floating_ct(self):
        file_path, _ = QFileDialog().getOpenFileName(self, 'Select Floating CT Scan', '.', '(*)')
        if file_path:
            log.debug(f"Loading floating CT from {file_path}")
            self.floating_ct_path = file_path
            self.floating_ct_label.setText(f"Loaded: {os.path.basename(file_path)}")
            
            # Create a CT object from the file
            self.floating_ct = CT(self.controller.config)
            self.floating_ct.load(file_path, self.controller.config['ct_threshold'])
            
            self.update_ui_state()
            
    def load_coordinates(self):
        file_path, _ = QFileDialog().getOpenFileName(self, 'Select Coordinates File', '.', '(*.json *.txt)')
        ct = CT(self.controller.config)
        self.coordinates_data = {}
        if file_path:
            log.debug(f"Loading coordinates from {file_path}")
            self.coords_file_path = file_path
            self.coords_label.setText(f"Loaded: {os.path.basename(file_path)}")
            
            # Load the coordinates
            if file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    self.coordinates_data = json.load(f)
            else:  # txt file
                parsed_leads = ct.from_vox_mom_parser(file_path)
                self.coordinates_data = parsed_leads
            self.update_ui_state()
            
    def register_ct_scans(self):
        """Register the floating CT to the reference CT using SimpleITK"""
        if not self.ref_ct or not self.floating_ct:
            QMessageBox.warning(self, 'Registration Error', 
                              'Both reference and floating CT scans must be loaded')
            return
            
        log.debug("Registering CT scans")
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        try:
            # Fallback method: direct affine transformation
            # Extract transformation matrices from CT headers
            ref_affine = self.ref_ct.affine
            floating_affine = self.floating_ct.affine
            # Make sure that the affine matrices are square
            if ref_affine.shape[0] == 3 and ref_affine.shape[1] == 4:
                ref_affine = np.vstack([ref_affine, [0, 0, 0, 1]])
            if floating_affine.shape[0] == 3 and floating_affine.shape[1] == 4:
                floating_affine = np.vstack([floating_affine, [0, 0, 0, 1]])
            log.debug(f"Reference CT affine: {ref_affine}")
            log.debug(f"Floating CT affine: {floating_affine}")
            # Calculate the transformation from floating to reference
            self.registration_transform = np.linalg.inv(ref_affine) @ floating_affine
            self.progress_bar.setValue(90)
            # Update UI
            self.register_status.setText("Registered with fallback method ✓")
            self.update_ui_state()
            self.progress_bar.setValue(100)
            QMessageBox.information(self, 'Registration Complete', 
                                        'Successfully registered CT scans using fallback method')
        except Exception as nested_e:
            log.error(f"Fallback registration failed: {str(nested_e)}")
            QMessageBox.warning(self, 'Registration Error', 
                                f'Failed to register CT scans: {str(e)}\nFallback also failed: {str(nested_e)}')
        finally:
            self.progress_bar.setVisible(False)
    
    def transform_coordinates(self):
        """Transform coordinates from floating space to reference space"""
        if self.registration_transform is None:
            log.warning("Transformation attempted without registration")
            QMessageBox.warning(self, 'Transformation Error', 
                                     'CT scans must be registered first')
            return
            
        try:
            # Apply transformation to coordinates
            transformed_data = self.apply_transform_to_coordinates(self.coordinates_data)
            
            # Prompt for save location
            save_file, _ = QFileDialog().getSaveFileName(self, 
                                                           'Save Transformed Coordinates', 
                                                           '.', 
                                                           'JSON (*.json);;TXT (*.txt)')
            if save_file:
                # Save transformed coordinates
                if save_file.endswith('.json'):
                    with open(save_file, 'w') as f:
                        json.dump(transformed_data, f, indent=2)
                else:  # txt file
                    # Implement txt saving based on your format
                    with open(save_file, 'w') as f:
                        for lead_name, lead_data in transformed_data.items():
                            f.write(f"{lead_name} \t{lead_data['x']} \t{lead_data['y']} \t{lead_data['z']} \t{lead_data['lead_type']} \t{lead_data['dim_x']} \t{lead_data['dim_y']}\n")                        
                
                QMessageBox.information(self, 'Transformation Complete', 
                                            f'Transformed coordinates saved to {save_file}')
                
        except Exception as e:
            log.error(f"Coordinate transformation failed: {str(e)}")
            QMessageBox.warning(self, 'Transformation Error', 
                                    f'Failed to transform coordinates: {str(e)}')
    
    def apply_transform_to_coordinates(self, coordinates_data):
        """Apply registration transform to coordinates"""
        '''     
        coordinates_data looks like this:        
        parsed_leads[contact_name] = {
                'x': float(x),
                'y': float(y),
                'z': float(z),
                'lead_type': lead_type,
                'dim_x': int(dim_x),
                'dim_y': int(dim_y)
            }
        '''
        transformed_data = coordinates_data.copy()

        # Apply the transformation to each coordinate
        for lead_name, lead_data in coordinates_data.items():
            # Extract the original coordinates
            original_coords = np.array([lead_data['x'], lead_data['y'], lead_data['z'], 1.0])
            # Apply the transformation
            transformed_coords = self.registration_transform @ original_coords
            # Update the coordinates in the transformed data
            transformed_data[lead_name]['x'] = transformed_coords[0]
            transformed_data[lead_name]['y'] = transformed_coords[1]
            transformed_data[lead_name]['z'] = transformed_coords[2]
        
        return transformed_data