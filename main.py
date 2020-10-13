import logging
from rsdd_enums import *
from sentinel2image import *
from processdata import *
from tests import *
from filters import *
import utils

def filterDirtyCsv():
    addCloudColBand()
    addSnapCol()
    assertFullCsvs()
    addCloudColImg()
    addVegetationIdexes()
    cleanCloudsAndNumber()
    addQuadrantsToPointsCsv()
    moveSnaps()
    sortCsvs()
    updatePointImgClass()

def generateNewRSSDVersion():
    makeBandsCsv()
    makeImgsPointsSnaps()

def getClassesByQuadrant():
    with open(Paths.ResultPath + 'classPorQuadrante.csv', 'w', newline='',encoding='utf-8') as tabelaF, \
         open(Paths.ResultPath + 'class-points.csv') as pointsF:
        pointsCsv = csv.reader(pointsF)
        table = csv.writer(tabelaF)
        next(pointsCsv)
        table.writerow(['Quadrante','0-Consevado','1-Desmatado','2-Útil','3-Milagre'])
        ClassesByQuadrant = dict()
        for i in range(1,26):
            ClassesByQuadrant[i] = {0:0,1:0,2:0,3:0}
        for line in pointsCsv:
            quadrant = int(line[-1])
            pointClass = int(line[-2])
            ClassesByQuadrant[quadrant][pointClass] += 1
        print(ClassesByQuadrant[12])
        for quadrant in sorted(ClassesByQuadrant):
            line = [quadrant]
            for pointClass in sorted(ClassesByQuadrant[quadrant]):
                line.append(ClassesByQuadrant[quadrant][pointClass])
            table.writerow(line)
def main():
    generateNewRSSDVersion()
    filterDirtyCsv()
    #getClassesByQuadrant()
    getPreseverdPoints()

if __name__ == '__main__':
    with open('log.txt','w'): pass
    logging.basicConfig(filename="log.txt", \
                            filemode='a+', \
                            level=logging.DEBUG)
    main()



    