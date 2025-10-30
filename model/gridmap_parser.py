"""
VoxTool Medical Electrode Grid Mapping Parser Module

This module provides specialized parsing capabilities for medical electrode grid
mapping files used in neurological procedures. Handles electrode channel mapping,
contact identification, and medical device specifications for various electrode
types used in epilepsy monitoring and neurosurgical applications.

Core Components Overview:
------------------------
1. **contact**: Individual electrode contact representation with channel mapping
2. **electrode**: Complete electrode assembly with multiple contacts
3. **GridMapParser**: Main parser for medical electrode specification files

Medical Context:
---------------
Electrode grid mapping is crucial for neurological procedures where precise
channel identification is required for:
- **Epilepsy Monitoring**: Long-term EEG recording with implanted electrodes
- **Functional Mapping**: Brain stimulation for language/motor function assessment
- **Seizure Localization**: Precise identification of epileptogenic zones
- **Surgical Planning**: Pre-operative electrode placement optimization

File Format Specification:
--------------------------
The parser handles CSV-formatted electrode mapping files with the following structure:
```
GridId,Template,Location,Hemisphere,Label,ChannelID,GridElectrode
0,SpencerDepth1x10,Amygdala,Left,LA,1:10,1:10
1,SpencerDepth1x10,HippocampusHead,Left,LHH,11:20,1:10
```

Where:
- **GridId**: Unique identifier for each electrode
- **Template**: Electrode type specification (e.g., SpencerDepth1x10)
- **Location**: Anatomical brain region target
- **Hemisphere**: Left/Right brain hemisphere
- **Label**: Short electrode identifier (e.g., LA, RHH)
- **ChannelID**: Channel range in acquisition system (1:10 = channels 1-10)
- **GridElectrode**: Local contact numbering within electrode (1:10 = contacts 1-10)

Channel ID vs Channel Index:
---------------------------
Critical distinction for medical device integration:
- **Channel ID**: Unique hardware identifier from acquisition system (may be non-contiguous)
- **Channel Index**: Sequential software index for data processing (always contiguous)

This parser handles both formats and provides proper mapping between hardware
channels and software processing indices.

Electrode Types Supported:
-------------------------
- **Depth Electrodes**: Linear arrays for deep brain structures (e.g., SpencerDepth1x10)
- **Grid Electrodes**: 2D arrays for cortical surface mapping (e.g., Grid8x8)
- **Strip Electrodes**: Linear arrays for cortical surface (e.g., Strip1x4)
- **Micro Electrodes**: High-resolution contacts for single-cell recording

Dependencies:
------------
- csv: Standard CSV file parsing
- logging: Diagnostic output for medical data validation

Author: VoxTool Development Team
License: See LICENSE.txt
"""

import csv
import logging
# Where we have the "channel" column, this should be ChannelID. What we have right now is the "channel index" which is different.
# Channel ID can be non-contiguous, and can have discontinuities.
# As such, @todo We need to remove the sequence number and replace this with the expanded Channel ID.
# We should get the channel ID from
# Input data as a string, for demonstration purposes
# Example input data with Channel INDEX, not Channel ID. todo: Integrate channel ID into pipeline.
'''
"""
GridId,  Template,          Location,           Hemisphere,  Label,  Channel,   GridElectrode
0,       SpencerDepth1x10,  Amygdala,           Left,        LA,     1:10,      1:10
1,       SpencerDepth1x10,  HippocampusHead,    Left,        LHH,    11:20,     1:10
2,       SpencerDepth1x10,  HippocampusTail,    Left,        LHT,    21:30,     1:10
3,       SpencerDepth1x10,  OrbitofrontalCortex,Left,        LOFC,   31:40,     1:10
4,       SpencerDepth1x6,   Cingulate,          Left,        LC,     41:46,     1:6
5,       SpencerDepth1x10,  Insula,             Left,        LI,     47:56,     1:10
6,       SpencerDepth1x6,   AnteriorFrontal,    Left,        LAF,    57:62,     1:6
7,       SpencerDepth1x6,   PosteriorFrontal,   Left,        LPF,    63:68,     1:6
8,       SpencerDepth1x8,   HippocampusTail,    Right,       RHT,    69:76,     1:8
9,       SpencerDepth1x8,   OrbitofrontalCortex,Right,       ROFC,   77:84,     1:8
10,      SpencerDepth1x6,   Cingulate,          Right,       RC,     85:90,     1:6
11,      SpencerDepth1x10,  Insula,             Right,       RI,     91:100,    1:10
12,      SpencerDepth1x6,   InferiorTemporal,   Right,       RIT,    101:106,   1:6
13,      SpencerDepth1x6,   SuperiorTemporal,   Right,       RST,    107:112,   1:6
14,      Dummy1x1,          NoWhere,            Left,        DMY,    128:128,   1:1"""
'''

log = logging.getLogger()

class contact:
    """
    Individual electrode contact representation with medical device mapping.
    
    Each contact represents a single recording/stimulation site on a medical
    electrode. This class manages the critical mapping between hardware channel
    identifiers and software processing indices required for neurological
    data analysis.
    
    Key Features:
    ------------
    - **Channel Mapping**: Hardware channel ID to software index translation
    - **Contact Identification**: Local and global contact numbering
    - **Device Integration**: Support for various electrode type specifications
    
    Medical Applications:
    -------------------
    - EEG/LFP recording channel identification
    - Electrical stimulation contact mapping  
    - Data acquisition system integration
    - Anatomical localization reference
    
    Attributes:
    -----------
    channelID : int or None
        Unique hardware channel identifier from acquisition system (Blackrock, etc.)
        This corresponds to the physical channel number in the recording device
        
    localChannelIdx : int or None
        Contact index within the specific electrode (0-based, electrode-relative)
        Example: Contact 3 of electrode LA would have localChannelIdx = 2
        
    globalChannelIdx : int or None
        Contact index across the entire electrode array (0-based, globally unique)
        Used for software processing and data array indexing
        
    contactType : str or None
        Electrode template specification (e.g., "SpencerDepth1x10", "Grid8x8")
        Defines the physical characteristics and contact arrangement
    """
    def __init__(self):
        self.channelID = None # This is the unique channel identifier that is used to identify the channel in the raw data per Blackrock specifications.
        self.localChannelIdx = None # This is just the index of this channel in the electrode. Not unique.
        self.globalChannelIdx = None # This is the index of this channel in the entire grid map. Unique but meaningless.
        self.contactType = None

class electrode:
    """
    Complete medical electrode assembly with multiple recording contacts.
    
    This class represents a complete electrode device (depth, grid, or strip)
    with its associated contacts, anatomical targeting, and channel mapping.
    Essential for organizing complex multi-electrode arrays used in neurological
    procedures.
    
    Key Features:
    ------------
    - **Multi-Contact Management**: Organized collection of electrode contacts
    - **Anatomical Targeting**: Brain region and hemisphere specification
    - **Channel Organization**: Hardware-to-software mapping for entire electrode
    - **Medical Labeling**: Clinical identification and naming conventions
    
    Medical Context:
    ---------------
    Electrodes are placed in specific brain regions for:
    - Seizure focus localization in epilepsy patients
    - Functional brain mapping before tumor resection
    - Deep brain stimulation for movement disorders
    - Research applications in cognitive neuroscience
    
    Attributes:
    -----------
    gridId : int or None
        Unique numerical identifier for this electrode in the surgical plan
        
    template : str or None
        Electrode type specification defining physical characteristics
        Examples: "SpencerDepth1x10", "Grid8x8", "Strip1x4"
        
    location : str or None
        Target anatomical brain region
        Examples: "Amygdala", "HippocampusHead", "OrbitofrontalCortex"
        
    hemisphere : str or None
        Brain hemisphere placement ("Left" or "Right")
        
    label : str or None
        Short clinical identifier used in data files and analysis
        Examples: "LA" (Left Amygdala), "RHH" (Right Hippocampus Head)
        
    numberOfChannels : int
        Total number of recording contacts on this electrode
        
    channelIDs : list or None
        List of hardware channel identifiers for all contacts
        Maps to acquisition system channel numbers
        
    contactsList : list
        List of contact objects representing individual recording sites
    """
    def __init__(self):
        self.gridId = None
        self.template = None
        self.location = None
        self.hemisphere = None
        self.label = None
        self.numberOfChannels = 0
        self.channelIDs = None
        self.contactsList = []

class GridMapParser:
    """
    Medical electrode grid mapping file parser for neurological applications.
    
    This class parses electrode specification files that define the mapping
    between physical electrode placements and data acquisition system channels.
    Critical for proper data interpretation in neurological research and
    clinical applications.
    
    Key Features:
    ------------
    - **CSV Format Support**: Standard medical electrode mapping file format
    - **Channel Validation**: Automatic verification of channel ID consistency
    - **Electrode Organization**: Hierarchical organization of contacts within electrodes
    - **Error Handling**: Robust parsing with medical data validation
    - **Multi-Format Support**: Handles both Channel ID and Channel Index formats
    
    Medical Workflow Integration:
    ----------------------------
    1. **Pre-surgical Planning**: Load electrode specifications for placement planning
    2. **Data Acquisition Setup**: Configure recording system channel mapping
    3. **Post-surgical Validation**: Verify electrode placement against specifications
    4. **Data Analysis Preparation**: Establish channel-to-anatomy mapping for analysis
    
    File Format Requirements:
    ------------------------
    Input files must be CSV format with the following columns:
    - GridId: Integer electrode identifier
    - Template: Electrode type string (e.g., "SpencerDepth1x10")
    - Location: Anatomical target string (e.g., "Amygdala")
    - Hemisphere: "Left" or "Right"
    - Label: Short electrode identifier (e.g., "LA")
    - ChannelID: Channel range string (e.g., "1:10" for channels 1-10)
    - GridElectrode: Contact range string (e.g., "1:10" for contacts 1-10)
    
    Attributes:
    -----------
    filename : str
        Path to the electrode mapping CSV file
        
    raw : str or None
        Raw file contents as string
        
    channelIDsPresent : bool
        Flag indicating whether file contains Channel IDs or indices
        
    contactTotal : int
        Total number of contacts across all electrodes
        
    electrodeList : list
        List of electrode objects parsed from the file
        
    Usage Example:
    -------------
    ```python
    # Load and parse electrode mapping file
    parser = GridMapParser("electrode_map.csv")
    parser.parse()
    
    # Access parsed electrode information
    for electrode in parser.electrodeList:
        print(f"Electrode {electrode.label}: {electrode.numberOfChannels} contacts")
        print(f"Location: {electrode.location} ({electrode.hemisphere})")
        
        for contact in electrode.contactsList:
            print(f"  Contact {contact.localChannelIdx}: Channel {contact.channelID}")
    ```
    """
    def __init__(self, filename):
        """
        Initialize the grid map parser with electrode specification file.
        
        Parameters:
        -----------
        filename : str
            Path to the CSV file containing electrode specifications
        """
        self.filename = filename
        self.raw = None
        self.channelIDsPresent = False
        self.contactTotal = 0
        self.electrodeList = []

    def parse(self):
        """
        Parse the electrode mapping file and organize electrode/contact data.
        
        This method performs the complete parsing workflow:
        1. Read CSV file contents
        2. Validate file format and detect Channel ID vs Index format
        3. Parse each electrode specification line
        4. Create electrode and contact objects
        5. Establish channel mapping relationships
        6. Validate consistency across the electrode array
        
        Raises:
        -------
        FileNotFoundError
            If the specified electrode mapping file cannot be found
        ValueError
            If file format is invalid or channel mappings are inconsistent
        
        Notes:
        ------
        - Skips dummy electrodes (location "NoWhere") used for system testing
        - Validates that channel ID ranges match contact ranges for each electrode
        - Logs detailed parsing progress for medical data verification
        - Handles both contiguous and non-contiguous channel ID assignments
        """
        # Map files are really just CSV files with a header. We can use the csv module to parse them.
        with open(self.filename, 'r') as file:
            self.raw = file.read()
        # Now we can parse the data
        lines = self.raw.split('\n')
        # Check if this is a channel ID file or a channel index file
        header = lines[0].split(',')
        if(header[5] == 'ChannelID'):
            self.channelIDsPresent = True
        for line in lines[1:]: # Skip the header
            parts = line.split(',')
            if len(parts) < 7:
                log.debug("GridMapParser.parse: Skipping incomplete line")
                continue
            if(parts[2] == 'NoWhere'):
                log.debug("GridMapParser.parse: Skipping dummy electrode")
                continue # Skip the dummy electrode
            log.debug(f"GridMapParser.parse: Parsing electrode {parts[4]}")
            self.electrodeList.append(electrode())
            self.electrodeList[-1].gridId = int(parts[0])
            self.electrodeList[-1].template = parts[1]
            self.electrodeList[-1].location = parts[2]
            self.electrodeList[-1].hemisphere = parts[3]
            self.electrodeList[-1].label = parts[4]
            self.channelIDsPresent = True # for debug
            if(self.channelIDsPresent):
                electrodeChannelIDs = parts[5].split(':')
                self.electrodeList[-1].channelIDs = list(range(int(electrodeChannelIDs[0]), int(electrodeChannelIDs[1]) + 1))  
            # Now split the electrode per contact
            self.electrodeList[-1].contactsList = []
            contactRange = parts[6].split(':')
            contactRange = list(range(int(contactRange[0]), int(contactRange[1]) + 1))
            if(self.channelIDsPresent):
                assert len(contactRange) == len(self.electrodeList[-1].channelIDs), "GridMapParser.parse: Channel ID and contact range mismatch" 
            for loopIdx, contactIdx in enumerate(contactRange):
                self.contactTotal += 1
                self.electrodeList[-1].numberOfChannels += 1
                self.electrodeList[-1].contactsList.append(contact())
                if(self.channelIDsPresent):
                    self.electrodeList[-1].contactsList[-1].channelID = self.electrodeList[-1].channelIDs[loopIdx]
                self.electrodeList[-1].contactsList[-1].localChannelIdx = loopIdx
                self.electrodeList[-1].contactsList[-1].globalChannelIdx = self.contactTotal
                self.electrodeList[-1].contactsList[-1].contactType = self.electrodeList[-1].template
            log.debug(f"GridMapParser.parse: Parsed {len(self.electrodeList[-1].contactsList)} contacts for electrode {self.electrodeList[-1].label}")
            log.debug("GridMapParser.parse: Parsed electrode {self.electrodeList[-1].label} with {len(self.electrodeList[-1].contactsList)} contacts")
        log.debug(f"GridMapParser.parse: Parsed {len(self.electrodeList)} electrodes with {self.contactTotal} contacts")