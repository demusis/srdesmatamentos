import os
import rasterio
from os import sep as slash
import utils
import logging
from rsdd_enums import *
log = logging.getLogger(__name__)
logging.getLogger('rasterio').setLevel(logging.CRITICAL)

class Sentinel2Image:
    """Groups the rasterio datasets of a single image and some metadata"""
    def __init__(self,imageDataPath,onlyRGB=False):
        """Instanciates a Sentinel2Imagem from its dataPath"""
        self.bands = [] if onlyRGB else [None] * 13
        self.bandsNames = [] if onlyRGB else [None] * 13
        self.isRgb = onlyRGB
        with os.scandir(imageDataPath) as imageSCND:
            for imgFolderItem in sorted(imageSCND, key=lambda e: e.name):
                if imgFolderItem.is_dir():
                    self.day = imgFolderItem.name[11:15]
                    self.month = imgFolderItem.name[15:17]
                    self.year = imgFolderItem.name[17:19]
                    self.nameDiscriminator = imgFolderItem.name[-27:-5] #Needed because snap unity
                    granulePath = imageDataPath + slash + imgFolderItem.name + \
                         slash + "GRANULE" + slash
                    #log.debug("Granule path is: " + granulePath)
                    with os.scandir(granulePath) as granuleSCND:
                        for granuleItem in sorted(granuleSCND, key=lambda e: e.name):
                            imgDataPath = granulePath + granuleItem.name + \
                                 slash + "IMG_DATA" + slash
                            #log.debug("IMG_DATA path is: " + imgDataPath)
                            with os.scandir(imgDataPath) as imgDataSCND:
                                for band in sorted(imgDataSCND, key=lambda e: e.name):
                                    bandPath = imgDataPath + slash + band.name
                                    if onlyRGB and Bands.TCI.Id in band.name:
                                        #log.debug("loading TCI: " + band.name)
                                        self.bands.append(rasterio.open(bandPath))
                                        self.bandsNames.append(band.name)
                                        return None
                                    elif not onlyRGB and Bands.TCI.Id not in band.name:
                                        #log.debug("loading band: " + band.name)
                                        index = utils.bandIdToIndex( \
                                            utils.getBandIdFromBandPath(band.name))
                                        self.bands[index] = rasterio.open(bandPath)
                                        self.bandsNames[index] = band.name
                                return None

    def __del__(self):
        for band in self.bands:
            band.close()
