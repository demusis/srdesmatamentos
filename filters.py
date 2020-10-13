import csv
from decimal import Decimal
import os
import rasterio
import rasterio.errors
from rsdd_enums import *
from utils import *
from collections import Counter
import pandas as pd
import shutil
import logging
log = logging.getLogger(__name__)
logging.getLogger('rasterio').setLevel(logging.CRITICAL)

def addCloudColBand(RemoveCloudShadow=True,oldBandsClass=CsvFileClass.Dirty,colN=8,append=False):
    """Add the cloud column into bandsCsv"""
    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Cloud
    dirtyBandsCsv = FileNames.BandsCsv%oldBandsClass
    fileMode = "a+" if append else "w"
    with open(Paths.ResultPath + bandsCsvName, fileMode, newline='') as resultFile, \
         open(Paths.ResultPath + dirtyBandsCsv, 'r') as bandsFile:
        resultCsv = csv.writer(resultFile)
        bandsCsv = csv.reader(bandsFile)
        if not append:
            header = next(bandsCsv)
            header.insert(colN,'Cloud')
            header.insert(colN+1,'CloudShadow')
            resultCsv.writerow(header)
        cloudTif = None
        cloudTifData = None
        imgName = None
        FindFirstError = False
        for line in bandsCsv:
            if FindFirstError and line[4] != "L1C_T21LZH_A010789_20170716T140424":#FMASK doesn't exist 
                continue
            else:
                FindFirstError = False
            pointId = int(line[0])
            lon = float(line[5])
            lat = float(line[6])
            cloudVal = 0
            shadowVal = 0
            #Loads new FMask if the image name changes
            if line[4] != imgName:
                log.debug("loading Fmask for: %s %s"%(line[4],line[0]))
                imgName = line[4]
                if cloudTif is not None:
                    cloudTif.close()
                fmaskPath = Paths.DataPath + line[4] + os.sep + FileNames.FMaskTif
                if os.path.isfile(fmaskPath):
                    cloudTif = rasterio.open(fmaskPath)
                    cloudTifData = cloudTif.read(1)
                else:
                    cloudTif = None
                    cloudTifData = None
            if cloudTifData is not None:
                lonC,latC, = convertPointCrs(lon,lat,destCrs=cloudTif.crs)
                row, col = cloudTif.index(lonC, latC)
                if cloudTifData[row,col] == FMaskInfo.Cloud:
                    cloudVal = 1
                if cloudTifData[row,col] == FMaskInfo.CloudShadow:
                    shadowVal = 1
            line.insert(colN,cloudVal)
            line.insert(colN+1,shadowVal)
            resultCsv.writerow(line)

def addSnapCol(bandsCsvSourceClass=CsvFileClass.Cloud,imgsCsvSourceClass=CsvFileClass.Dirty,res=20):
    """Add snap name column"""
    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Snapshot
    oldBandsCsv = FileNames.BandsCsv%bandsCsvSourceClass
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Snapshot
    oldImgsCsv = FileNames.ImgsCsv%imgsCsvSourceClass 
    with open(Paths.ResultPath + oldImgsCsv, 'r') as imgsFile, \
         open(Paths.ResultPath + oldBandsCsv, 'r') as bandsFile, \
         open(Paths.ResultPath + imgsCsvName, 'w', newline='') as imgsFiltradoFile, \
         open(Paths.ResultPath + bandsCsvName, 'w', newline='') as bandsFiltradoFile:
        
        imgsCsv = csv.reader(imgsFile)
        imgsResultCsv = csv.writer(imgsFiltradoFile)
        imgsHeader = next(imgsCsv)
        imgsHeader.append('Snapshot')
        imgsResultCsv.writerow(imgsHeader)
        bandsCsv = csv.reader(bandsFile)
        bandsResultCsv = csv.writer(bandsFiltradoFile)
        bandsHeader = next(bandsCsv)
        bandsHeader.append('Snapshot')
        bandsResultCsv.writerow(bandsHeader)
        log.debug("Start adding to imgs.csv")
        for line in imgsCsv:
            snapName = f"{res:04}_{int(line[1]):05}_{line[0][4:10]}_{line[0][-15:]}.png"
            line.append(snapName)
            imgsResultCsv.writerow(line)
        log.debug("Start adding to bands.csv")
        for line in bandsCsv:
            snapName = f"{res:04}_{int(line[0]):05}_{line[4][4:10]}_{line[4][-15:]}.png"
            line.append(snapName)
            bandsResultCsv.writerow(line)

def assertFullCsvs(oldBandsClass=CsvFileClass.Snapshot,oldImgsClass=CsvFileClass.Snapshot, \
    oldPointsClass=CsvFileClass.Dirty,removeSnaps=True):
    """Make sure that only entries that appear on all places stays"""
    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Asserted
    oldBandsCsv = FileNames.BandsCsv%oldBandsClass
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Asserted
    oldImgsCsv = FileNames.ImgsCsv%oldImgsClass
    pointsCsvName = FileNames.PointsCsv%CsvFileClass.Asserted
    oldPointsCsv = FileNames.PointsCsv%oldPointsClass 
    with open(Paths.ResultPath + oldPointsCsv, 'r') as pointsFile, \
         open(Paths.ResultPath + oldImgsCsv, 'r') as imgsFile, \
         open(Paths.ResultPath + oldBandsCsv, 'r') as bandsFile, \
         open(Paths.ResultPath + pointsCsvName, 'w', newline='') as pointsFiltradoFile, \
         open(Paths.ResultPath + imgsCsvName, 'w', newline='') as imgsFiltradoFile, \
         open(Paths.ResultPath + bandsCsvName, 'w', newline='') as bandsFiltradoFile:
        
        pointsCsv = csv.reader(pointsFile)
        imgsCsv = csv.reader(imgsFile)
        bandsCsv = csv.reader(bandsFile)
        pointsFiltradoCsv = csv.writer(pointsFiltradoFile)
        imgsFiltradoCsv = csv.writer(imgsFiltradoFile)
        bandsFiltradoCsv = csv.writer(bandsFiltradoFile)
        pointsFiltradoCsv.writerow(next(pointsCsv))
        imgsFiltradoCsv.writerow(next(imgsCsv))
        bandsFiltradoCsv.writerow(next(bandsCsv))
        
        validImgsNames = set()
        strangeImagesList = []
    
        #See whats names the snap folder contains
        for img in os.scandir(Paths.SnapsPath):
            validImgsNames.add(img.name)
    
        for line in imgsCsv:
            if line[-1] in validImgsNames:
                strangeImagesList.append(line[-1])
        imgsFile.seek(0)
        log.debug(imgsCsv)
        log.debug("%s validos por snap e img"%len(validImgsNames))
        
        strangeImagesCounter = Counter(strangeImagesList)
        #Ve se tem snaps repetidas no img.csv
        for strange in strangeImagesCounter.most_common():
            if strange[1] == 1:
                break
            if strange[0] in validImgsNames:
                validImgsNames.remove(strange[0])
        
        log.debug("%s validos sem repetido"%len(validImgsNames))

        bandsNames = set()
        badBands = set()
        bandsCountLines = []
        #Remove os que tiverem dados nulos nas bandas ou que não tiverem os dados de todas
        #Também remove as banda que não estiverem completas
        for line in bandsCsv:
            bandsCountLines.append(line[-1])
            bandsNames.add(line[-1])
            if "0" in line[10:-1] or '' in line[10:-1] or len(line[10:-1]) != 13:
                badBands.add(line[-1])
        bandsFile.seek(0)
        next(bandsCsv)
        inter = validImgsNames.intersection(bandsNames)
        valid =  inter - badBands

        #Remove bandas inconpletas
        bandsLinesCounter = Counter(bandsCountLines)

        for key in bandsLinesCounter.most_common()[-1::-1]:
            if key[1] != 36 and key[0] in valid:
                valid.remove(key[0])
        
        print(len(validImgsNames), len(bandsNames),len(badBands), len(inter), len(valid))
        validPoints = set()
        
        log.debug("final era para ter %s e %s"%(len(valid),36*len(valid)))
        
        for validEntry in valid:
            validPoints.add(int(validEntry[5:10]))
        
        #Salva os novos csvs
        for line in pointsCsv:
            if int(line[0]) in validPoints:
                pointsFiltradoCsv.writerow(line)
        
        for line in imgsCsv:
            if line[-1] in valid:
                imgsFiltradoCsv.writerow(line)

        for line in bandsCsv:
            if line[-1] in valid:
                bandsFiltradoCsv.writerow(line)

        if removeSnaps:
            if not os.path.isdir(Paths.LostPath):
                os.makedirs(Paths.LostPath)
            #Remove as imagens de pontos que não são válidos        
            for img in os.scandir(Paths.SnapsPath):
                if img.name not in valid and img.is_file():
                    shutil.move(f"{Paths.SnapsPath}{img.name}", f"{Paths.LostPath}{img.name}")

def addCloudColImg(oldBandsClass=CsvFileClass.Asserted,oldImgsClass=CsvFileClass.Asserted,colNumber=5):
    """Add cloud column to imgs csv"""
    oldBandsCsv = FileNames.BandsCsv%oldBandsClass
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Cloud
    oldImgsCsv = FileNames.ImgsCsv%oldImgsClass
    with open(Paths.ResultPath + oldBandsCsv, 'r') as bandsFile, \
         open(Paths.ResultPath + oldImgsCsv, 'r') as imgsFile, \
         open(Paths.ResultPath + imgsCsvName, 'w', newline='') as resultFile:
        bandsCsv = csv.reader(bandsFile)
        imgsCsv = csv.reader(imgsFile)
        resultCsv = csv.writer(resultFile)
        header = next(imgsCsv)
        header.insert(colNumber,'Cloud')
        header.insert(colNumber+1,'CloudShadow')
        resultCsv.writerow(header)
        next(bandsCsv)
        cloudSumDict = dict()
        cloudShadowSumDict = dict()
        for line in bandsCsv:
            if line[-1] not in cloudSumDict:
                cloudSumDict[line[-1]] = 0
            if line[-1] not in cloudShadowSumDict:
                cloudShadowSumDict[line[-1]] = 0
            cloudSumDict[line[-1]] += int(line[8])
            cloudShadowSumDict[line[-1]] += int(line[9])

        for line in imgsCsv:
            line.insert(colNumber,cloudSumDict[line[-1]])
            line.insert(colNumber+1,cloudShadowSumDict[line[-1]])
            resultCsv.writerow(line)

def addVegetationIdexes(oldBandsClass=CsvFileClass.Asserted):
    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Ndvi
    oldBandsCsv = FileNames.BandsCsv%oldBandsClass
    #Why latin3 idkw
    bandas = pd.read_csv(Paths.ResultPath + oldBandsCsv, encoding="latin3")
    bandas.columns = ["PointId","Day","Month","Year",'ImgName', "Longitude","Latitude", "Index","Cloud","CloudShadow", "Band1", "Band2", "Band3", "Band4", "Band5", "Band6", "Band7", "Band8", "Band8a", "Band9", "Band10", "Band11", "Band12","Snap"]
    bandas.describe()
    # Calculo de indices

    # NDVI = (band8 - band4) / (band8 + band4)
    bandas['ndvi'] = bandas.apply(lambda row: (row.Band8 - row.Band4) / (row.Band8 + row.Band4), axis=1)

    # SAVI = (band8 - band4) / (band8 + band4 + 0.5) * 1.5
    bandas['savi'] = bandas.apply(lambda row: (row.Band8 - row.Band4) / (row.Band8 + row.Band4 + 0.5) * 1.5, axis=1)
    bandas.to_csv(Paths.ResultPath + bandsCsvName, encoding='utf-8', index=False)

def cleanCloudsAndNumber(oldBandsClass=CsvFileClass.Ndvi,oldImgsClass=CsvFileClass.Cloud, \
    oldPointsClass=CsvFileClass.Asserted,removeSnaps=False,cloudTreshold=0, \
    imgCountTreshold = 6,skipCountFilter=True,removeExcess=False,skipDesforetationFilter=True):
    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Cleaned
    oldBandsCsv = FileNames.BandsCsv%oldBandsClass
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Cleaned
    oldImgsCsv = FileNames.ImgsCsv%oldImgsClass
    pointsCsvName = FileNames.PointsCsv%CsvFileClass.Cleaned
    oldPointsCsv = FileNames.PointsCsv%oldPointsClass 
    with open(Paths.ResultPath + oldPointsCsv, 'r') as pointsFile, \
        open(Paths.ResultPath + oldImgsCsv, 'r') as imgsFile, \
        open(Paths.ResultPath + oldBandsCsv, 'r') as bandsFile, \
        open(Paths.ResultPath + pointsCsvName, 'w', newline='') as pointsFiltradoFile, \
        open(Paths.ResultPath + imgsCsvName, 'w', newline='') as imgsFiltradoFile, \
        open(Paths.ResultPath + bandsCsvName, 'w', newline='') as bandsFiltradoFile:

        pointsCsv = csv.reader(pointsFile)
        imgsCsv = csv.reader(imgsFile)
        bandsCsv = csv.reader(bandsFile)
        pointsFiltradoCsv = csv.writer(pointsFiltradoFile)
        imgsFiltradoCsv = csv.writer(imgsFiltradoFile)
        bandsFiltradoCsv = csv.writer(bandsFiltradoFile)
        pointHeader = next(pointsCsv)
        pointHeader.append("Diff")
        pointHeader.append("Class")
        pointsFiltradoCsv.writerow(pointHeader)
        imgHeader = next(imgsCsv)
        imgHeader.append("NDVI")
        imgHeader.append("SAVI")
        imgsFiltradoCsv.writerow(imgHeader)
        bandsFiltradoCsv.writerow(next(bandsCsv))
        
        imgsNoCloud = set()
        
        for line in imgsCsv:
            if int(line[5]) <= cloudTreshold:
                imgsNoCloud.add(line[-1])
        imgsFile.seek(0)
        next(imgsCsv)
        
        print("%s imagens sem nuvens"%len(imgsNoCloud))
        
        validImgsByPoint = dict()
        for img in imgsNoCloud:
            pointId = int(img[5:10])
            if pointId not in validImgsByPoint:
                validImgsByPoint[pointId] = []
            imgDate = img[18:26]
            foundDate = False
            for imgName in validImgsByPoint[pointId]:
                if imgName[18:26] == imgDate:
                    foundDate = True
            if not foundDate:
                validImgsByPoint[pointId].append(img)
        
        validPoints = set()
        print("%s pontos sem datas repetidas"%len(validImgsByPoint))
        
        numImgs = 0
        for point in validImgsByPoint:
            numImgs += len(validImgsByPoint[point])
            
        print("%s total de imgs por pontos"%numImgs)
        
        imgIndicadores = dict()
        
        for line in bandsCsv:
            imageId = line[-3]
            if imageId not in imgIndicadores:
                imgIndicadores[imageId] = ([0],[0])
                #0 = NDVI 1 = SAVI
            imgIndicadores[imageId][0][0] += float(line[-2])
            imgIndicadores[imageId][1][0] += float(line[-1])
        bandsFile.seek(0)
        next(bandsCsv)
        
        for img in imgIndicadores:
            imgIndicadores[img][0][0] /= 36
            imgIndicadores[img][1][0] /= 36
        
        imgsNotDeforested = dict()
        pointIndicadores = dict()
        
        desC = 0
        for point in validImgsByPoint:
            imgsSortedDate = sorted(validImgsByPoint[point], key= lambda e: e[-15:-7])
            #pega da imagem mais antiga
            oldestNdvi = imgIndicadores[imgsSortedDate[0]][0][0] 
            newestNdvi = imgIndicadores[imgsSortedDate[-1]][0][0] 
            if point not in pointIndicadores:
                pointIndicadores[point] = ([0],[0])
            #0 = diff 1 = class
            pointIndicadores[point][0][0] = newestNdvi - oldestNdvi
            #Se o último NDVI for maior que 0.55 => conservado[0]
            #Se o primeiro NDVI for menor que 0.55 => desmatado[1]
            #Se começou conservado e terminou desmatado[2] 
            pointIndicadores[point][1][0] = 0 if newestNdvi > 0.55\
                else 1 if oldestNdvi < 0.55 else 2
                    
            if oldestNdvi > 0.55 or skipDesforetationFilter:
                imgsNotDeforested[point] = validImgsByPoint[point]
            else:
                desC += 1
                # if '20170701' not in imgsSortedDate[0]:
                #     print("ZZZ")
                #     for name in imgsSortedDate:
                #         print(name)
                #     print("ZZZ")
                # print(imgsSortedDate[0][-15:-7])
                # print("nome da primeira img %s"%imgsSortedDate[0])
                # print("Ponto %s removido por desmatado"%point)
        valid = dict()
        
        print("Removidos pelo NDVI %s"%desC)
        #print("%s imagens que começaram conservadas"%len(imgsNotDeforested))
        
        countC = 0
        for pointId in imgsNotDeforested:
            if skipCountFilter:
                validPoints.add(pointId)
                valid[pointId] = imgsNotDeforested[pointId]
            elif len(imgsNotDeforested[pointId]) >= imgCountTreshold:
                validPoints.add(pointId)
                if removeExcess:
                    selectedImgs = spacedSelect(imgsNotDeforested[pointId], imgCountTreshold)
                    valid[pointId] = selectedImgs
                else:
                    valid[pointId] = imgsNotDeforested[pointId]
            else:
                print("Ponto %s removido por não ter imagens suficientes %s"%(pointId,len(imgsNotDeforested[pointId])))
                countC += 1
                
                
        print("Removidos %s por falta de imagem"%countC)
        print("%s pontos válidos"%len(valid))
        #Salva os novos csvs
        for line in pointsCsv:
            if int(line[0]) in validPoints:
                #Adiciona diff e class
                line.append(pointIndicadores[int(line[0])][0][0])
                line.append(pointIndicadores[int(line[0])][1][0])
                pointsFiltradoCsv.writerow(line)
        
        for line in imgsCsv:
            #Adiciona média dos indicadores
            if int(line[1]) in valid:
                imgName = line[-1]
                if imgName in valid[int(line[1])]:
                    line.append(imgIndicadores[imgName][0][0])
                    line.append(imgIndicadores[imgName][1][0])
                    imgsFiltradoCsv.writerow(line)

        for line in bandsCsv:
            if int(line[0]) in valid:
                imgName = line[-3]
                if imgName in valid[int(line[0])]:
                    bandsFiltradoCsv.writerow(line)
        if removeSnaps:
            #Remove as imagens de pontos que não são válidos
            allValidSnaps = set()
            for point in valid:
                for snapName in valid[point]:
                    allValidSnaps.add(snapName)    
            for img in os.scandir(Paths.SnapsPath):
                if not os.path.isdir(Paths.CleanedPath):
                    os.makedirs(Paths.CleanedPath)
                if img.name not in allValidSnaps and img.is_file():
                    shutil.move(f"{Paths.SnapsPath}{img.name}", f"{Paths.CleanedPath}{img.name}")

def assertFullCsvs2(oldBandsClass=CsvFileClass.Cleaned,oldImgsClass=CsvFileClass.Cleaned, \
    oldPointsClass=CsvFileClass.Cleaned,removeSnaps=False):
    """Make sure that only entries that appear on all places stays"""
    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Asserted2
    oldBandsCsv = FileNames.BandsCsv%oldBandsClass
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Asserted2
    oldImgsCsv = FileNames.ImgsCsv%oldImgsClass
    pointsCsvName = FileNames.PointsCsv%CsvFileClass.Asserted2
    oldPointsCsv = FileNames.PointsCsv%oldPointsClass 
    with open(Paths.ResultPath + oldPointsCsv, 'r') as pointsFile, \
         open(Paths.ResultPath + oldImgsCsv, 'r') as imgsFile, \
         open(Paths.ResultPath + oldBandsCsv, 'r') as bandsFile, \
         open(Paths.ResultPath + pointsCsvName, 'w', newline='') as pointsFiltradoFile, \
         open(Paths.ResultPath + imgsCsvName, 'w', newline='') as imgsFiltradoFile, \
         open(Paths.ResultPath + bandsCsvName, 'w', newline='') as bandsFiltradoFile:
        
        pointsCsv = csv.reader(pointsFile)
        imgsCsv = csv.reader(imgsFile)
        bandsCsv = csv.reader(bandsFile)
        pointsFiltradoCsv = csv.writer(pointsFiltradoFile)
        imgsFiltradoCsv = csv.writer(imgsFiltradoFile)
        bandsFiltradoCsv = csv.writer(bandsFiltradoFile)
        pointsFiltradoCsv.writerow(next(pointsCsv))
        imgsFiltradoCsv.writerow(next(imgsCsv))
        bandsFiltradoCsv.writerow(next(bandsCsv))
        
        validImgsNames = set()
        strangeImagesList = []
    
        #Ve as imagens que foram geradas
        for img in os.scandir(Paths.SnapsPath):
            validImgsNames.add(img.name)
    
        for line in imgsCsv:
            if line[-3] in validImgsNames:
                strangeImagesList.append(line[-3])
        imgsFile.seek(0)
        log.debug(imgsCsv)
        log.debug("%s validos por snap e img"%len(validImgsNames))
        
        strangeImagesCounter = Counter(strangeImagesList)
        #Ve se tem snaps repetidas no img.csv
        for strange in strangeImagesCounter.most_common():
            if strange[1] == 1:
                break
            if strange[0] in validImgsNames:
                validImgsNames.remove(strange[0])
        
        log.debug("%s validos sem repetido"%len(validImgsNames))

        bandsNames = set()
        badBands = set()
        #Remove os que tiverem dados nulos nas bandas ou que não tiverem os dados de todas
        for line in bandsCsv:
            bandsNames.add(line[-3])
            if "0" in line[10:-3] or '' in line[10:-3] or len(line[10:-3]) != 13:
                badBands.add(line[-3])
        bandsFile.seek(0)
        next(bandsCsv)
        inter = validImgsNames.intersection(bandsNames)
        valid =  inter - badBands
        print(len(validImgsNames), len(bandsNames),len(badBands), len(inter), len(valid))
        validPoints = set()
        
        log.debug("final era para ter %s e %s"%(len(valid),36*len(valid)))
        
        for validEntry in valid:
            validPoints.add(int(validEntry[5:10]))
        
        #Salva os novos csvs
        for line in pointsCsv:
            if int(line[0]) in validPoints:
                pointsFiltradoCsv.writerow(line)
        
        for line in imgsCsv:
            if line[-3] in valid:
                imgsFiltradoCsv.writerow(line)

        for line in bandsCsv:
            if line[-3] in valid:
                bandsFiltradoCsv.writerow(line)

        if removeSnaps:
            if not os.path.isdir(Paths.Lost2Path):
                os.makedirs(Paths.Lost2Path)
            #Remove as imagens de pontos que não são válidos        
            for img in os.scandir(Paths.SnapsPath):
                if img.name not in valid and img.is_file():
                    shutil.move(f"{Paths.SnapsPath}{img.name}", f"{Paths.Lost2Path}{img.name}")

def addQuadrantsToPointsCsv(nQuadrants=5,oldPointsClass=CsvFileClass.Cleaned):
    pointsCsvName = FileNames.PointsCsv%CsvFileClass.Quadrant
    oldPointsCsv = FileNames.PointsCsv%oldPointsClass         
    with open(Paths.ResultPath + oldPointsCsv, 'r') as pointsOF, \
         open(Paths.ResultPath + pointsCsvName, 'w', newline='') as pointsRF:
        pointsOCsv = csv.reader(pointsOF)
        pointsResultCsv = csv.writer(pointsRF)
        header = next(pointsOCsv)
        header.append('Quadrant')
        pointsResultCsv.writerow(header)
        for line in pointsOCsv:
            line.append(getQuadrant(float(line[1]),float(line[2])))
            pointsResultCsv.writerow(line)

def moveSnaps(oldBandsClass=CsvFileClass.Cleaned,oldImgsClass=CsvFileClass.Cleaned, \
    oldPointsClass=CsvFileClass.Quadrant):
   
    if not os.path.isdir(Paths.SnapsPath + '1' + os.sep):
        for i in range(1,26):
            os.mkdir(Paths.SnapsPath + str(i))

    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Final
    oldBandsCsv = FileNames.BandsCsv%oldBandsClass
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Final
    oldImgsCsv = FileNames.ImgsCsv%oldImgsClass
    oldPointsCsv = FileNames.PointsCsv%oldPointsClass 
    with open(Paths.ResultPath + oldImgsCsv) as imgsFile, \
         open(Paths.ResultPath + oldPointsCsv) as pointsFile, \
         open(Paths.ResultPath + oldBandsCsv) as bandsFile, \
         open(Paths.ResultPath + bandsCsvName, 'w', newline='') as bandsRFile, \
         open(Paths.ResultPath + imgsCsvName, 'w', newline='') as imgsRFile:
        
        imgsCsv = csv.reader(imgsFile)
        pointsCsv = csv.reader(pointsFile)
        bandsCsv = csv.reader(bandsFile)
        bandsR = csv.writer(bandsRFile)
        imgsR = csv.writer(imgsRFile)
        bandsR.writerow(next(bandsCsv))
        imgsR.writerow(next(imgsCsv))
        next(pointsCsv)
        
        quadrantByPoint = dict()
        for line in pointsCsv:
            quadrantByPoint[int(line[0])] = line[-1]
        
        ndviEntries = dict()
        for line in imgsCsv:
            pointId = int(line[1])
            ndviEntries[line[-3]] = [line[-2],pointId,f"{(float(line[-2]) + 2):1.5f}_{line[-3]}"]
        
        for img in os.scandir(Paths.SnapsPath):
            if img.is_file():
                if img.name in ndviEntries:                    
                    quadrant = quadrantByPoint[ndviEntries[img.name][1]]
                    newName = ndviEntries[img.name][2] 
                    shutil.move(f"{Paths.SnapsPath}{img.name}", f"{Paths.SnapsPath}{str(quadrant)}{os.sep}{newName}")
        
        imgsFile.seek(0)
        next(imgsCsv)
        
        for line in imgsCsv:
            line[-3] = ndviEntries[line[-3]][2]
            imgsR.writerow(line)
            
        for line in bandsCsv:
            line[-3] = ndviEntries[line[-3]][2]
            bandsR.writerow(line)

def sortCsvs(oldBandsClass=CsvFileClass.Final,oldImgsClass=CsvFileClass.Final, \
    oldPointsClass=CsvFileClass.Quadrant):
    #Watch enconding
    bandsCsvName = FileNames.BandsCsv%CsvFileClass.Sorted
    oldBandsCsv = FileNames.BandsCsv%oldBandsClass
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Sorted
    oldImgsCsv = FileNames.ImgsCsv%oldImgsClass
    pointsCsvName = FileNames.PointsCsv%CsvFileClass.Sorted
    oldPointsCsv = FileNames.PointsCsv%oldPointsClass 

    points = pd.read_csv(Paths.ResultPath + oldPointsCsv, float_precision='round_trip')
    points.sort_values(["PointId"])
    points.to_csv(Paths.ResultPath + pointsCsvName, encoding='utf-8', index=False)
    
    imgs = pd.read_csv(Paths.ResultPath + oldImgsCsv, float_precision='round_trip')
    imgs.sort_values(["PointId","Year","Month","Day"])
    imgs.to_csv(Paths.ResultPath + imgsCsvName, encoding='utf-8', index=False)

    bands = pd.read_csv(Paths.ResultPath + oldBandsCsv, float_precision='round_trip')
    bands.sort_values(["PointId","Year","Month","Day","Index"],inplace=True)
    bands.to_csv(Paths.ResultPath + bandsCsvName, encoding='utf-8', index=False)

def updatePointImgClass(oldImgsClass=CsvFileClass.Sorted, oldPointsClass=CsvFileClass.Sorted):
    
    imgsCsvName = FileNames.ImgsCsv%CsvFileClass.Class
    oldImgsCsv = FileNames.ImgsCsv%oldImgsClass
    pointCsvName = FileNames.PointsCsv%CsvFileClass.Class
    oldPointsCsv = FileNames.PointsCsv%oldPointsClass 
    
    with open(Paths.ResultPath + oldImgsCsv) as imgsFile, \
         open(Paths.ResultPath + oldPointsCsv) as pointsFile, \
         open(Paths.ResultPath + pointCsvName, 'w', newline='') as pointsRFile, \
         open(Paths.ResultPath + imgsCsvName, 'w', newline='') as imgsRFile:
        
        imgsCsv = csv.reader(imgsFile)
        pointsCsv = csv.reader(pointsFile)
        imgsR = csv.writer(imgsRFile)
        pointsR = csv.writer(pointsRFile)
        pointsR.writerow(next(pointsCsv))
        imgsHeader = next(imgsCsv)
        imgsHeader.append("Class")
        imgsR.writerow(imgsHeader)
        
        #        Quadrant MIN    MAX
        tresholds = {1 : (0.51,	0.61),
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
        quadrantByPoint = dict()

        for line in pointsCsv:
            quadrantByPoint[int(line[0])]= int(line[-1])
        pointsFile.seek(0)
        next(pointsCsv)
        #Se  NDVI for maior que treshold => conservado[0]
        #Se  NDVI for menor que treshold => desmatado[1]
        #Se  não => intermediário[2]

        classesByPoints = dict()
        debugDates = dict()
        for line in imgsCsv:
            ndvi = float(line[-2])
            pointId = int(line[1])
            ndviClass = 0 if ndvi > tresholds[quadrantByPoint[pointId]][1] else \
                        1 if ndvi < tresholds[quadrantByPoint[pointId]][0] else 2
            debugDate = (line[2],line[3],line[4],ndviClass)
            log.debug(f"{pointId} => {debugDate}")
            if pointId not in classesByPoints:
                classesByPoints[pointId] = []
                debugDates[pointId] = []
            classesByPoints[pointId].append(ndviClass)
            debugDates[pointId].append(debugDate)
            line.append(ndviClass)
            imgsR.writerow(line)
        
        #0 se começo e final são conservados
        #1 se começou desmatado
        #2 Começou conservado e terminou desmatado
        #3 Começou desmatado e terminou conversvado
        for line in pointsCsv:
            pointId = int(line[0])
            log.debug(f"{pointId}: {classesByPoints[pointId][0]} / {classesByPoints[pointId][-1]}")
            log.debug(f"{debugDates[pointId]}")
            pointClass = 0 if classesByPoints[pointId][0] == 0 and classesByPoints[pointId][-1] == 0 else \
                         1 if classesByPoints[pointId][0] == 1 and classesByPoints[pointId][-1] == 1 else \
                         2 if classesByPoints[pointId][0] == 0 and classesByPoints[pointId][-1] == 1 else 3
            line[-2] = pointClass
            pointsR.writerow(line)

def cleanByClass(folderPath,desiredClass):
    points = pd.read_csv(folderPath + 'points.csv')
    points2Remove = list(points[points['Class'] != desiredClass].PointId)
    pointsClean = points[~points['PointId'].isin(points2Remove)]
    pointsClean.to_csv(folderPath+'pointsClassClean.csv',index=False)
    imgs = pd.read_csv(folderPath + 'imgs.csv')
    imgsClean = imgs[~imgs['PointId'].isin(points2Remove)]
    imgsClean.to_csv(folderPath+'imgsClassClean.csv',index=False)
    bands = pd.read_csv(folderPath + 'bands.csv')
    bandsClean = bands[~bands['PointId'].isin(points2Remove)]
    bandsClean.to_csv(folderPath+'bandsClassClean.csv',index=False)
    if not os.path.isdir(folderPath + 'snaps\\outliers\\'):
                os.makedirs(folderPath + 'snaps\\outliers\\')
    for entry in os.scandir(folderPath+'snaps\\'):
        if entry.is_dir() and entry.name.isnumeric():
            for img in os.scandir(folderPath+'snaps\\'+entry.name+'\\'):
                pointId = int(img.name[13:18])
                if pointId in points2Remove:
                    shutil.move(folderPath+'snaps\\'+entry.name+'\\'+img.name,\
                                folderPath+'snaps\\outliers\\'+img.name)