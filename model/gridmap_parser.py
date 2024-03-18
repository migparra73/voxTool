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
    def __init__(self):
        self.channelID = None # This is the unique channel identifier that is used to identify the channel in the raw data per Blackrock specifications.
        self.localChannelIdx = None # This is just the index of this channel in the electrode. Not unique.
        self.globalChannelIdx = None # This is the index of this channel in the entire grid map. Unique but meaningless.
        self.contactType = None

class electrode:
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
    def __init__(self, filename):
        self.filename = filename
        self.raw = None
        self.channelIDsPresent = False
        self.contactTotal = 0
        self.electrodeList = []

    def parse(self):
        # Map files are really just CSV files with a header. We can use the csv module to parse them.
        with open(self.filename, 'r') as file:
            self.raw = file.read()
        # Now we can parse the data
        lines = self.raw.split('\n')
        # Check if this is a channel ID file or a channel index file
        header = lines[0].split(',')
        if(header[5] == 'ChannelID'):
            self.channelIDsPresent = True
        for line in lines[1:-1]: # Skip the header
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