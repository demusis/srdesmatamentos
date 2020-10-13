from rsdd_enums import *
from decimal import Decimal
from rasterio.warp import transform
from rasterio.crs import CRS
import numpy as np
import logging
import geopy.distance
from random import random
log = logging.getLogger(__name__)
logging.getLogger('rasterio').setLevel(logging.CRITICAL)

def getBandIdFromBandPath(bandPath):
    """Obtains an image band id from its path"""
    return bandPath[-6:-4]

def bandIdToIndex(bandId):
    """Map an image band id(like 8a) to its respective index"""
    if len(bandId) > 2:
        print(len(bandId),bandId)
        bandId = bandId[-6:-4]
    if bandId.isnumeric():
        index = int(bandId)
        assert index < 13, "unexpected band index, should be less than 13"
        if (bandId <= Bands.Nir.Id):
            return index - 1
        else:
             return index
    else:
        assert '8A' in bandId, "unexpected band, should be 8A"
        return 8

def parseLineOriginCsv(line):
    """Parse a line from origin csv into its respectives vars and types"""
    return int(line[OriginCsvLineInfo.PointId]), \
        Decimal(line[OriginCsvLineInfo.Longitude]), \
        Decimal(line[OriginCsvLineInfo.Latitude]), \
        Decimal(line[OriginCsvLineInfo.Deforested]),\
        eval(line[OriginCsvLineInfo.DisplayIdList])

def getBoundingBox(imgCrs,lon,lat,nPoints,area):
    """Return the boudingbox of an AOI and the gap between the points"""
    lonConv,latConv = convertPointCrs(lon,lat,destCrs=imgCrs)
    gap = area / nPoints
    step = area / 2.0
    east = lonConv + step 
    west = lonConv - step
    north = latConv + step
    south = latConv - step
    log.debug(f"W S E N:{west},{south},{east},{north}")
    return (west,south,east,north),gap

def checkBoundingBox(boundingBoxOriginal,boundingBoxWindow):
    error = []
    if boundingBoxOriginal[Directions.West] <= boundingBoxWindow[Directions.West]:
        if boundingBoxOriginal[Directions.South] <= boundingBoxWindow[Directions.South]:
            if boundingBoxOriginal[Directions.East] >= boundingBoxWindow[Directions.East]:
                if boundingBoxOriginal[Directions.North] >= boundingBoxWindow[Directions.North]:
                    return True,error
                else:
                    log.debug(f'Directions.North.value => {boundingBoxOriginal[Directions.North]} <= {boundingBoxWindow[Directions.North]}')
                    error.append(Directions.North)
            else:
                log.debug(f'Directions.East.value => {boundingBoxOriginal[Directions.East]} <= {boundingBoxWindow[Directions.East]}')
                error.append(Directions.East)
        else:
            log.debug(f'Directions.South.value => {boundingBoxOriginal[Directions.South]} >= {boundingBoxWindow[Directions.South]}')
            error.append(Directions.South)
    else:
        log.debug(f'Directions.West.value => {boundingBoxOriginal[Directions.West]} >= {boundingBoxWindow[Directions.West]}')
        error.append(Directions.West)
    return False,error

def getWkt(wn,es):
    """Return de wkt from a quadrilateral"""
    w = wn[0]
    n = wn[1]
    e = es[0]
    s = es[1]
    return f"POLYGON (({w} {n}, {e} {n}, {e} {s}, {w} {s}, {w} {n}))"

def convertPointCrs(lon,lat,orgCrs=CRS.from_epsg(4326),destCrs=CRS.from_epsg(4326)):
    """Do the crs convertion of a point"""
    lonConv,latConv = transform(orgCrs,destCrs,[lon],[lat])
    lonConv = lonConv[0]
    latConv = latConv[0]
    return lonConv,latConv

def spacedSelect(items, n):
    selecteds = []
    if len(items) == n:
        selecteds = items
    else:
        if n >= 1:
            selecteds.append(items[0])
        if n >= 2:
            selecteds.append(items[-1])
        if n >= 3:
            indexes = np.linspace(0,len(items)-1,n)
            #print(indexes)
            for i in indexes[1:-1]:
                selecteds.append(items[int(i)])
            #print(len(selecteds))
    return sorted(selecteds)

def getQuadrant(lon,lat,gridLimits=None,nQuadrants=5):
    if gridLimits is None:
        gridLimits = []
        xStart = -61.6328245855
        xStep = 2.28169357892
        yStart = -7.348647867
        yStep = -2.13849721204
        xs = []
        ys = []
        for i in range(nQuadrants+1):
            xs.append(xStart + i * xStep)
        for i in range(nQuadrants+1):
            ys.append( yStart + i * yStep)
        for i in range(1,nQuadrants+1):
            for j in range(1,nQuadrants+1):
                sqr = ((xs[j-1],xs[j]),(ys[i],ys[i-1]))
                gridLimits.append(sqr)
    for sqr in gridLimits:
        if lon >= sqr[0][0] and lon <= sqr[0][1]:
            if lat >= sqr[1][0] and lat <= sqr[1][1]:
                return gridLimits.index(sqr) + 1
    raise Exception('Não achou o quadrante D:')

def spiral_generator(lon,lat):
    ang = random() * 360
    step = 0.01
    sPoint = geopy.distance.distance(kilometers = step)\
             .destination(point=geopy.Point((lat,lon)),\
                          bearing=ang)
    lon,lat = sPoint[1],sPoint[0]
    yield lon,lat
    distStep = 0.001
    angStep = 5
    while True:
        ang = (ang + angStep) %360
        step += distStep
        sPoint = geopy.distance.distance(kilometers = step)\
                .destination(point=geopy.Point((lat,lon)),\
                             bearing=ang)
        lon,lat = sPoint[1],sPoint[0]
        yield lon,lat
