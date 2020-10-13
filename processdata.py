import csv
import os
import json
import pandas as pd
from rasterio.windows import from_bounds as windowFromBounds
from rasterio.windows import transform as getWindowTransform

from rsdd_enums import *
from sentinel2image import *
from utils import *
from snap import *
import logging
log = logging.getLogger(__name__)
logging.getLogger('rasterio').setLevel(logging.CRITICAL)

def writeBands(bandWriter,dataPath,lon,lat,imgName,pointId,nPoints = 6, area = 60):
    """Write the data from the bands of a point inside a image into bands.csv"""
    sentinel2Image = Sentinel2Image(dataPath + imgName + os.sep)
    baseLine = [pointId,sentinel2Image.year,sentinel2Image.month,\
                sentinel2Image.day,imgName]
    imgData = []
    transforms = []
    #Used to bring more data for the window, because without this scale
    #the window may not contain all the data of the AOI
    expandFactor = 6 
    expandedBoundingBox,_ = getBoundingBox(sentinel2Image.bands[0].crs,lon,lat,nPoints,area * expandFactor)
    log.debug(getWkt((expandedBoundingBox[3],expandedBoundingBox[0]), \
        (expandedBoundingBox[1],expandedBoundingBox[2])))
    for band in sentinel2Image.bands:
        bandData = []
        bandWin = rasterio.windows.from_bounds(*expandedBoundingBox, band.transform).round_offsets()        
        transforms.append(rasterio.windows.transform(bandWin,band.transform))
        bandData = band.read(1,window=bandWin)
        imgData.append(bandData)
    
    aoiPoints = []
    aoiBoudingBox,_ = getBoundingBox(sentinel2Image.bands[0].crs,lon,lat,nPoints,area)
    #The red band is utilized to calculate the AOI points because it resolution(10m)
    redWindow = windowFromBounds(*aoiBoudingBox, \
        sentinel2Image.bands[Bands.Red.Index].transform)
    redWindowTransform = getWindowTransform(redWindow,\
        sentinel2Image.bands[Bands.Red.Index].transform)
    for row in range(nPoints):
        for col in range(nPoints):
            pLon,pLat = rasterio.transform.xy(redWindowTransform,row,col)
            pLonC,pLatC, = convertPointCrs(pLon,pLat,\
                orgCrs=sentinel2Image.bands[Bands.Red.Index].crs)
            bandIndex = row * 6 + col + 1
            aoiPoints.append((pLon,pLat,pLonC,pLatC,bandIndex))
            
    for point in aoiPoints:
        lineData = [point[AOIPointsInfo.LonC],\
                    point[AOIPointsInfo.LatC],\
                    point[AOIPointsInfo.Index]]
        for band,bandIndex in zip(imgData,range(13)):
            row,col = rasterio.transform.rowcol(transforms[bandIndex],\
                point[AOIPointsInfo.Lon],point[AOIPointsInfo.Lat])
            lineData.append(band[row,col])
        bandWriter.writerow(baseLine + lineData)

def makeBandsCsv(resultPath = Paths.ResultPath,dataPath = Paths.DataPath, \
    limit = -1, start = 0):
    """Build the bands csv without any filter"""
    log.debug("Starting generate the bands csv")
    bandFileName = FileNames.BandsCsv%CsvFileClass.Dirty
    fileMode = 'w' if start == 0 else 'a+'
    with open(Paths.OriginCsvPath, 'r') as originCsvFile, \
         open(resultPath + bandFileName, mode=fileMode, newline='') as bandFile:
        originCsv = csv.reader(originCsvFile)
        next(originCsv)
        bandWriter = csv.writer(bandFile)
        if fileMode == 'w':
            bandWriter.writerow(['PointId', 'Day', 'Month', 'Year','imgName',\
                                 'Longitude','Latitude','Index','Band 1 – Coastal aerosol', \
                                 'Band 2 – Blue', 'Band 3 – Green', 'Band 4 – Red', \
                                 'Band 5 – Vegetation red edge', 'Band 6 – Vegetation red edge', \
                                 'Band 7 – Vegetation red edge', 'Band 8 – NIR','Band 8A – Narrow NIR', \
                                 'Band 9 – Water vapour', 'Band 10 – SWIR – Cirrus', 'Band 11 – SWIR', \
                                 'Band 12 – SWIR'])

        nLinesRead = 0
        skipping = True if start != 0 else False
        for originLine in originCsv:
            
            nLinesRead += 1
            
            if start == nLinesRead and skipping:
                nLinesRead = 0
                skipping = False
            if skipping:
                continue
            pointId,lon,lat,_,imgList = parseLineOriginCsv(originLine)
            print(pointId)
            log.debug(f"adding images from: {pointId}")
            for imgName in imgList:
                try:
                    log.debug(f"Adding bands from: {imgName}")
                    writeBands(bandWriter,dataPath,lon,lat,imgName,pointId)
                except Exception as e:
                    log.critical(f"Error when tried to analyze {imgName} at point {pointId})")
                    log.debug(e)
                    log.debug("Outside image bb?")
                    log.debug("analyze this later")
            if nLinesRead == limit:
                return True

def makeImgsPointsSnaps(startRow = None,limit = None,res = 20):
    """Make the points.csv,imgs.csv and its respectives snaps"""
    log.debug("Starting generate the bands and points csv and snaps")
    if not os.path.isdir(Paths.SnapsPath):
        os.mkdir(Paths.SnapsPath)
    fileMode = 'w+' if startRow is None else 'a+'
    imgsFileName = FileNames.ImgsCsv%CsvFileClass.Dirty
    pointsFileName = FileNames.PointsCsv%CsvFileClass.Dirty
    with open(Paths.OriginCsvPath, 'r') as originalFile, \
         open(Paths.ScenesJsonPath, 'r') as scenesF, \
         open(Paths.ResultPath + imgsFileName, mode=fileMode, newline='') as imgsCsvF, \
         open(Paths.ResultPath + pointsFileName, mode=fileMode, newline='') as pointCsvF:
        scenesDict = json.load(scenesF)
        originalCsv = csv.reader(originalFile)
        imgsCsv = csv.writer(imgsCsvF)
        pointsCsv = csv.writer(pointCsvF)
        next(originalCsv)
        if fileMode == "w+":
            imgsCsv.writerow(['ImgName','PointId', 'Year', 'Month', 'Day','Image URL (Earth Explorer)', \
                             'ImageId (Earth Explorer)'])
            pointsCsv.writerow(['PointId', 'Longitude', 'Latitude', 'hectare deforested'])
        if startRow is not None:
            aux = 0
            while aux < startRow:
                next(originalCsv)
                aux += 1
        aux = 0
        for line in originalCsv:
            if limit is not None and aux == limit:
                break
            aux += 1
            pointId,lon,lat,deforested,imgList = parseLineOriginCsv(line)
            print(pointId)
            validPoint = False
            for imgName in imgList:
                if snapshotCsvLine(pointId,lon,lat,[imgName],res=res):
                    log.debug('Snap selected: %s'%imgName)
                    validPoint = True
                    #Make a function to parse date?
                    day = imgName[19:23]
                    month = imgName[23:25]
                    year = imgName[25:27]
                    imgsCsv.writerow([imgName,pointId,year,month,day,scenesDict[imgName]['downloadUrl'], \
                                                    scenesDict[imgName]['entityId']])
            if validPoint:
                pointsCsv.writerow([pointId,lon,lat,deforested])
            else:
                log.debug("%s delet by not having enough images"%pointId)


def getPreseverdPoints(oldImgsClass=CsvFileClass.Class,
                       oldPointsClass=CsvFileClass.Class,
                       oldBandsClass=CsvFileClass.Sorted):
    limit = 0
    pointsFileName = FileNames.PointsCsv%oldPointsClass
    imgsFileName = FileNames.ImgsCsv%oldImgsClass
    pointsCsv = pd.read_csv(Paths.ResultPath + pointsFileName)
    imgsCsv = pd.read_csv(Paths.ResultPath + imgsFileName)
    imgsByPoint = dict()
    rF = open(Paths.ResultPath + 'CoordeanadasComNome2017-final.csv','w',newline='')
    resultCsv = csv.writer(rF)
    resultCsv.writerow(["FID","Longitude","Latitude","hectares","displayId","displayIdList"])
    thresholds = {1 : (0.51,	0.61),
                     2 : (0.51,	0.65),
                     3 : (0.42,	0.64),
                     4 : (-2,-2), #NODATA
                     5 : (-2,-2), #NODATA
                     6 : (0.41,	0.65),
                     7 : (0.48,	0.68),
                     8 : (0.49,	0.60),
                     9 : (0.52,	0.58),
                     10 : (0.49,0.55),
                     11 : (0.48,0.57),
                     12 : (0.44,0.57),
                     13 : (0.50,0.58),
                     14 : (0.46,0.56),
                     15 : (0.48,0.55),
                     16 : (0.48,0.58),
                     17 : (0.50,0.64),
                     18 : (0.50,0.59),
                     19 : (0.46,0.54),
                     20 : (0.52,0.62),
                     21 : (0.50,0.63),
                     22 : (0.49,0.55),
                     23 : (0.48,0.61),
                     24 : (0.47,0.55),
                     25 : (-2,-2) #Few data
        }
    for i in imgsCsv.index:
        pId = imgsCsv['PointId'][i]
        if pId not in imgsByPoint:
            imgsByPoint[pId] = []
        imgsByPoint[pId].append(imgsCsv['ImgName'][i])

    for index in pointsCsv[pointsCsv['Class'] == 2].index:
        pointId = pointsCsv['PointId'][index]
        log.debug(f"Tentando {pointId}")
        print(f"Tentando {pointId}")
        quadrant = pointsCsv['Quadrant'][index]
        oLon = pointsCsv['Longitude'][index]
        oLat = pointsCsv['Latitude'][index]
        oldImg = Sentinel2Image(Paths.DataPath + imgsByPoint[pointId][0] + os.sep)
        oldNir = oldImg.bands[Bands.Nir.Index].read(1)
        oldRed = oldImg.bands[Bands.Red.Index].read(1)
        NDVI = (oldNir.astype(float) - oldRed.astype(float)) / (oldNir+oldRed)
        newImg = Sentinel2Image(Paths.DataPath + imgsByPoint[pointId][-1] + os.sep)
        newNir = newImg.bands[Bands.Nir.Index].read(1)
        newRed = newImg.bands[Bands.Red.Index].read(1)
        newNDVI = (newNir.astype(float) - newRed.astype(float)) / (newNir+newRed)
        spC = 0
        for lon,lat in spiral_generator(oLon,oLat):
            spC += 1
            if spC > 5000:
                break
            log.debug(f"Tentando ponto da espiral: {spC}")
            #lonC,latC = convertPointCrs(lon,lat,destCrs=oldImg.bands[Bands.Red.Index].crs)
            aoiPoints = []
            aoiBoudingBox,_ = getBoundingBox(oldImg.bands[Bands.Red.Index].crs,lon,lat,6,60)
            if not checkBoundingBox(oldImg.bands[Bands.Red.Index].bounds,aoiBoudingBox)[0]:
                log.debug("Fora do limite da imagem")
                continue
            #The red band is utilized to calculate the AOI points because it resolution(10m)
            redWindow = windowFromBounds(*aoiBoudingBox, \
                oldImg.bands[Bands.Red.Index].transform)
            redWindowTransform = getWindowTransform(redWindow,\
                oldImg.bands[Bands.Red.Index].transform)
            for row in range(6):
                for col in range(6):
                    pLon,pLat = rasterio.transform.xy(redWindowTransform,row,col)
                    #pLonC,pLatC, = convertPointCrs(pLon,pLat,\
                    #    orgCrs=oldImg.bands[Bands.Red.Index].crs)
                    #bandIndex = row * 6 + col + 1
                    #aoiPoints.append((pLon,pLat,pLonC,pLatC,bandIndex))
                    aoiPoints.append((pLon,pLat))
            #conservado = True
            ndviMean = 0
            for aoiPoint in aoiPoints:
                r,c = oldImg.bands[Bands.Red.Index].index(*aoiPoint)
                ndviMean += NDVI[r,c]
            ndviMean /= 36
            if ndviMean > thresholds[quadrant][1]:
                log.debug(f"{imgsByPoint[pointId][0]} antigo conservado")
                newNdviMean = 0
                notValid = False
                for aoiPoint in aoiPoints:
                    r,c = newImg.bands[Bands.Red.Index].index(*aoiPoint)
                    if r >= newNDVI.shape[0] or c >= newNDVI.shape[1] or r < 0 or c < 0:
                        notValid = True
                        break
                    newNdviMean += newNDVI[r,c]
                if notValid:
                    continue
                newNdviMean /= 36
                if newNdviMean > thresholds[quadrant][1]:
                    #limit += 1
                    log.debug("Achou um ponto novo")
                    log.debug(f"Quadrant {quadrant} {getQuadrant(lon,lat)}")
                    log.debug(f"lon lat {lon} {lat}")
                    log.debug(f"ndvis {thresholds[quadrant][1]} {ndviMean} {newNdviMean}")
                    log.debug(f"imgList {str(imgsByPoint[pointId])}")
                    resultCsv.writerow([pointId,lon,lat,0.0,imgsByPoint[pointId][0],str(imgsByPoint[pointId])])
                    if limit > 5:
                        rF.close()
                        return True
                    break
    return True
