import numpy as np
import os
import rasterio
import cv2
from utils import *
from rsdd_enums import *
from sentinel2image import *
import logging
logging.getLogger('numpy').setLevel(logging.CRITICAL)
log = logging.getLogger(__name__)

def normalizeBand(band):
    """Normalize the band data"""

    imin = np.nanmin(band)
    imax = np.nanmax(band)
    band_normed = (band - imin) / (imax - imin)
    return band_normed

def snap(resultPath,img,lon,lat,name,n = 200,markAoi=True):
    """Save a single rgb image made from rgb bands data"""

    imgMatrix = np.zeros((n,n,3), 'float64')
    tciDataset = img.bands[Bands.TCI.Index]
    boundingBox,_ = getBoundingBox(tciDataset.crs,lon,lat,1,n*10) # *10 por causa da resolução espacial
    boundingBoxBD,_ = getBoundingBox(tciDataset.crs,lon,lat,6,60)  # band data
    _,errorsAOI = checkBoundingBox(tciDataset.bounds,boundingBoxBD)
    if len(errorsAOI) > 0:
        log.debug("AOI out of image boudings:%s %s %s"%(name,errorsAOI,boundingBoxBD))
        return False
    _,errors = checkBoundingBox(tciDataset.bounds,boundingBox)
    log.debug("Bouding box errors: %s"%errors)
    limitImage = [0,0,0,0]
    for direction in range(Directions.West,Directions.North+1):
        limitImage[direction] = boundingBox[direction] if direction not in errors else tciDataset.bounds[direction]    
    log.debug("Image limits: %s"%limitImage)
    l = int((boundingBox[Directions.North] - tciDataset.bounds[Directions.North]) // 10) if Directions.North in errors else 0
    c = int((tciDataset.bounds[Directions.West] - boundingBox[Directions.West]) // 10) if Directions.West in errors else 0
    fullImageWin = rasterio.windows.from_bounds(*limitImage, tciDataset.transform).round_offsets()
    tr = rasterio.windows.transform(fullImageWin, tciDataset.transform)
    wn = rasterio.transform.rowcol(tr,boundingBoxBD[Directions.West],boundingBoxBD[Directions.North])
    es = rasterio.transform.rowcol(tr,boundingBoxBD[Directions.East],boundingBoxBD[Directions.South])
    log.debug("WN,ES: %s %s"%((boundingBoxBD[Directions.West],boundingBoxBD[Directions.North]),(boundingBoxBD[Directions.East],boundingBoxBD[Directions.South])))
    for i in range(1,4):
        try:
            bandData = tciDataset.read(i, window=fullImageWin)
        except rasterio.errors.RasterioIOError:
            log.debug("TCI image is corrupted: %s"%name)
            return False
        if  not bandData.any():
            log.debug("Empty image: "+ name)
            return False
        #Check if has nodata in AOI
        for row in range(wn[0],es[0]):
            for col in range(wn[1],es[1]):
                if bandData[row,col] == 0:
                    log.debug("AOI with no data: %s"%name)
                    return False
        bandData = normalizeBand(bandData) 
        imgMatrix[l:l+bandData.shape[0], c:c+bandData.shape[1], i-1] += bandData
        if markAoi:
            try:
                for iQ in range(wn[0]-1,es[0] + 1):
                    imgMatrix[iQ,wn[1] - 1,0] = 1.0
                    imgMatrix[iQ,wn[1] - 1,1] = 0
                    imgMatrix[iQ,wn[1] - 1,2] = 0
                    imgMatrix[iQ,es[1] + 0,0] = 1.0
                    imgMatrix[iQ,es[1] + 0,1] = 0
                    imgMatrix[iQ,es[1] + 0,2] = 0
                for jQ in range(wn[1] -1,es[1] + 1):
                    imgMatrix[wn[0] - 1,jQ,0] = 1.0
                    imgMatrix[wn[0] - 1,jQ,1] = 0
                    imgMatrix[wn[0] - 1,jQ,2] = 0
                    imgMatrix[es[0] + 0,jQ,0] = 1.0
                    imgMatrix[es[0] + 0,jQ,1] = 0
                    imgMatrix[es[0] + 0,jQ,2] = 0
            except Exception as e:
                log.critical(e)
                log.critical("AOI outside boundaries: " + name)
                return False
    imgMatrix[:,:,:] *= 255
    cv2.imwrite(resultPath + name + '.png',cv2.cvtColor(imgMatrix.astype('uint8'), cv2.COLOR_BGR2RGB))
    return True

def snapshotCsvLine(pId,lon,lat,imgsList,res = 200,dataPath=Paths.DataPath,resultPath=Paths.SnapsPath):
    """Takes info from a points csv line and give to snap"""
    for imgName in imgsList:
        imgPath = dataPath + imgName + os.sep
        log.debug("Loading: %s"%imgName)
        tciImage = Sentinel2Image(imgPath,onlyRGB=True)
        snapName = f'{int(res):04}_{int(pId):05}_{tciImage.nameDiscriminator}'
        return snap(resultPath,tciImage,lon,lat,snapName, n = res)