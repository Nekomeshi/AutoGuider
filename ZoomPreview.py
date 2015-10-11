import wx
import cv2
import threading
import AutoGuideSetup

SHIFT_UP = 1
SHIFT_DOWN = 2
SHIFT_LEFT = 3
SHIFT_RIGHT = 4


class ZoomPreview:
    __screenWidth = 0
    __screenHeight = 0
    __imgWidth = 0
    __imgHeight = 0
    __zoom = 0
    __drawArea = None #draw area in original image
    __zoomTable = []
    __lockDrawArea = None
    
    def __init__(self, screenWidth, screenHeight):
        self.__screenWidth = screenWidth
        self.__screenHeight = screenHeight
        
        self.__lockDrawArea = threading.Lock()
                
    def __calcDrawArea(self, direction = 0):
        if self.__drawArea == None:
            self.__lockDrawArea.acquire()
            self.__drawArea = wx.Rect(0, 0, self.__imgWidth, self.__imgHeight)
            self.__lockDrawArea.release()
            return
        
        cx = (self.__drawArea.GetLeft() + self.__drawArea.GetRight() + 1)/2
        cy = (self.__drawArea.GetTop() + self.__drawArea.GetBottom() + 1)/2
        z = self.__zoomTable[self.__zoom]
        sx = z[0]/2
        sy = z[1]/2
        l = cx - sx
        r = cx + sx
        if direction == SHIFT_LEFT:
            l = l - sx
            r = r - sx
        elif direction == SHIFT_RIGHT:
            l = l + sx
            r = r + sx            
        if l < 0:
            l = 0
        elif r >= self.__imgWidth:
            l = self.__imgWidth - z[0]
            
        t = cy - sy
        b = cy + sy
        if direction == SHIFT_UP:
            t = t - sy
            b = b - sy
        elif direction == SHIFT_DOWN:
            t = t + sy
            b = b + sy

        if t < 0:
            t = 0
        elif b >= self.__imgHeight:
            t = self.__imgHeight - z[1]
            
        self.__lockDrawArea.acquire()
        self.__drawArea = wx.Rect(l, t, z[0], z[1])
        self.__lockDrawArea.release()

    def setShift(self, direction):
        if len(self.__zoomTable) == 0:
            self.__zoom = 0
            return
        if self.__drawArea == None:
            return
        self.__calcDrawArea(direction)
        
    def setZoom(self, zoomUp):
        if len(self.__zoomTable) == 0:
            self.__zoom = 0
            return
        if self.__drawArea == None:
            return
        
        if zoomUp:
            self.__zoom = self.__zoom + 1
            if self.__zoom >= len(self.__zoomTable):
                self.__zoom = len(self.__zoomTable)-1
        else:
            self.__zoom = self.__zoom - 1
            if self.__zoom < 0:
                self.__zoom = 0
        self.__calcDrawArea()
        
    def __setZoomTable(self):
        w = self.__imgWidth
        h = self.__imgHeight
        self.__zoomTalbe = []
            
        while True:
            if h <= self.__screenHeight or w <= self.__screenWidth:
                self.__zoomTable = self.__zoomTable + [(self.__screenWidth, self.__screenHeight)]
                break;
            self.__zoomTable = self.__zoomTable + [(w, h)]
            w = w / 2
            h = h / 2
    def getPreviewArea(self):
        return self.__drawArea
    
    def drawPreview(self, frame):
        fH, fW = frame.shape[:2]
        if fH != self.__imgHeight or fW != self.__imgWidth:#initaial
            self.__imgHeight = fH
            self.__imgWidth = fW
            self.__setZoomTable()
            self.__calcDrawArea()
        #get crop area
        self.__lockDrawArea.acquire()        
        l = self.__drawArea.GetLeft() 
        r = self.__drawArea.GetRight()
        t = self.__drawArea.GetTop()
        b = self.__drawArea.GetBottom()
        self.__lockDrawArea.release()
        #crop
        zoom = frame[t:b, l:r]
        #set size to resize so that whole of screen is included in resized image
        zH, zW = zoom.shape[:2]
        screenAspect = float(self.__screenWidth)/float(self.__screenHeight)
        frameAspect = float(zW)/float(zH)
        if screenAspect < frameAspect:
            h = self.__screenHeight
            w = int(h*frameAspect)
        else:
            w = self.__screenWidth
            h = int(w/frameAspect)
        resized = cv2.resize(zoom, (w, h))
        if AutoGuideSetup.isShowPreviewBinary:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)#crop and gray
            if AutoGuideSetup.isThresAuto:
                ret, binImg = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)#binarize by otsu
            else:
                ret, binImg = cv2.threshold(gray, AutoGuideSetup.thresValue, 255, cv2.THRESH_BINARY)#binarize
            resized = cv2.cvtColor(binImg, cv2.COLOR_GRAY2BGR)
        else:
            pass
#            cv2.normalize(resized, resized, 0, 255, cv2.NORM_MINMAX)

        #when zoomed, draw zoom frame
        if self.__zoom > 0:
            scale = h*1.0/5.0/float(self.__imgHeight)     
            dW = w/2
            dH = h*4/5 - 10

            cv2.rectangle(resized, 
                        (dW, dH), 
                        (dW + int(self.__imgWidth*scale), dH + int(self.__imgHeight*scale)), 
                        (128, 0, 0), 1)
            cv2.rectangle(resized, 
                        (dW + int(l*scale), dH + int(t*scale)), 
                        (dW + int(r*scale), dH + int(b*scale)), 
                        (255, 0, 0), 1)
        
        return resized
