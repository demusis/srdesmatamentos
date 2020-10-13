class CsvFileClass:
    Result = ""
    Dirty = "dirty-"
    Cloud = "cloud-"
    Snapshot = "snap-"
    Asserted = "assert1-"
    Asserted2 = "assert2-"
    Ndvi = "ndvi-"
    Cleaned = "clean-"
    Quadrant = "quadrant-"
    Final = "final-"
    Sorted = "sorted-"
    Class = "class-"
    Preserved = "preserved-"
class FileNames:
    """Contains the file names used in the RSSD data process"""
    PointsCsv = "%spoints.csv"
    ImgsCsv = "%simgs.csv"
    BandsCsv = "%sbands.csv"
    OriginCsv = "CoordeanadasComNome2017-final.csv"
    ScenesJson = "scenes.json"
    FMaskTif = "cloud.tif"

class Paths:
    """Contains the paths that RSDD use"""
    #TODO: Parse a command line argument to set the data path
    DataPath = "D:\\RSDD\\ImagensSentinel2\\data\\"
    ResultPath = "D:\\RSDD\\Conservados\\"
    #ResultPath = "D:\\RSDD\\teste4Imgs\\"
    UtilFilesPath = "./utils/"
    OriginCsvPath = UtilFilesPath + FileNames.OriginCsv
    ScenesJsonPath = UtilFilesPath + FileNames.ScenesJson
    SnapsPath = ResultPath + 'snaps\\'
    LostPath = SnapsPath + 'lost\\'
    Lost2Path = SnapsPath + 'lost2\\'
    CleanedPath = SnapsPath + 'cleaned\\'
    # utils = "../utils/"
    # dataPath =  "D:\\RSDD\\ImagensSentinel2\\data\\"
    # dataPathWsl =  "/mnt/d/RSDD/ImagensSentinel2/data/"     
    # resultPath = ""
    # snapshotsPath = "snapshots\\"
    # scenes = "../utils/scenes.json"
    # file = "file.json"
    # pointsTxt = "points.txt"
    # originalCsv = "CoordeanadasComNome2017-final.csv"
    # imgCsv = "imgs.csv"
    # pointsCsv = "points.csv"
    # imgsCsv = "imgs.csv"
    # bandsCsv = "bands.csv"

class Directions:
    """Contains the indexes for using on the bounding boxes directions"""

    West = 0
    South = 1
    East = 2
    North = 3

class BandInfo:
    """Holds the information of a single band"""

    def __init__(self, bandId, index):
        self.Id = bandId
        self.Index = index

class Bands:
    """Contains the metadata about each sentinel 2 band"""
    TCI = BandInfo('TCI',0)
    Coastal = BandInfo('01',0)
    Blue = BandInfo('02',1)
    Green = BandInfo('03',2)
    Red = BandInfo('04',3)
    VegetationRedEdge1 = BandInfo('05',4)
    VegetationRedEdge2 = BandInfo('06',5)
    VegetationRedEdge3 = BandInfo('07',6)
    Nir = BandInfo('08',7)
    NarrowNir = BandInfo('8A',8)
    WaterVapour = BandInfo('09',9)
    SwirCirrus = BandInfo('10',10)
    Swir1 = BandInfo('11',11)
    Swir2 = BandInfo('12',12)

class OriginCsvLineInfo:
    """Indexes for the origin csv line data"""
    PointId = 0
    Longitude = 1
    Latitude = 2
    Deforested = 3
    DisplayIdList = 5

class AOIPointsInfo:
    """Indexes for the AOIPoints metadata"""
    Lon = 0
    Lat = 1
    LonC = 2
    LatC = 3
    Index = 4

class DateIndex:
    Year = 0
    Month = 1
    Day = 2

class FMaskInfo:
    """Indexes for FMask tif"""
    Null = 0
    Valid = 1
    Cloud = 2
    CloudShadow = 3
    Snow = 4
    Water = 5