import wx
import cv2
import AutoGuideSetup

class SearchGuideStar:
    def __init__(self):
        pass
        
    
    #frame:captured original image
    #searchArea:previewArea set in ZoomPreview.py
    def searchGuideStar(self, frame, searchArea = None):
        
        if searchArea != None:
            l = searchArea.GetLeft() 
            r = searchArea.GetRight()
            t = searchArea.GetTop()
            b = searchArea.GetBottom()
            searchFrame = frame[t:b, l:r]
        else:
            searchFrame = frame
            l = 0 
            t = 0
            b, r = frame.shape[:2]
            b = b-1
            r = r-1
        #find guide star here
        listLocation = []
        cnts = None
        try:
            gray = cv2.cvtColor(searchFrame, cv2.COLOR_BGR2GRAY)#crop and gray
            gray = cv2.GaussianBlur(gray, (3,3), 0) #de-noise by gaussian       
            if AutoGuideSetup.isThresAuto:
                ret, binImg = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)#binarize by otsu
            else:
                ret, binImg = cv2.threshold(gray, AutoGuideSetup.thresValue, 255, cv2.THRESH_BINARY)#binarize
            
            cnts = cv2.findContours(binImg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        except Exception, e:
            print e.message
            return None
        
        if cnts == None or len(cnts) == 0:
            print("bin img = {}".format(binImg))
            return None
        print("cont = {}".format(len(cnts)))
        for cnt in cnts:
            x,y,w,h = cv2.boundingRect(cnt)
            listLocation = listLocation + [wx.Rect(x, y, w, h)]
        
        listLocation.sort(cmp=self.__areaSizeCmp, reverse=False)#sort by Area size
        print("Loc {} {}, {}".format(listLocation[0], l, t))
        if searchArea != None:
            for loc in listLocation:#convert area value to base origin of original image origin.
                loc.OffsetXY(l, t)
                
        
        return listLocation
    #search guide star list from full_frame image
    #Stars that is in an area half screen size at each edge smaller than origial frame are detected 
    #frame: it should be full frame image
    def searchGuideStarInit(self, frame, screenWidth, screenHeight, searchArea = None):
#        h, w = frame.shape[:2]
#        halfW = screenWidth/2
#        halfH = screenHeight/2
#        print("searchGuideStarInit frame size = {}x{}, screen size = {}x{}".format(w, h, screenWidth, screenHeight))
#        okArea = wx.Rect(halfW, halfH, w - halfW, h - halfH)
        
        list = self.searchGuideStar(frame, searchArea)
        if list == None or len(list) == 0:
            return None
        return list
    
        list2 = []
        for loc in list:
            if not okArea.ContainsRect(loc):
                continue
            list2 = list2 + [loc]
        if len(list2) == 0:
            print("NoList")
            return None
        print("list2 {}".format(list2[0]))
        return list2
    
    def __areaSizeCmp(self, a, b):
        ax = a.GetWidth()*a.GetHeight()
        bx = b.GetWidth()*b.GetHeight()
        if ax > bx:
            return -1
        elif ax < bx:
            return 1
        else:
            return 0
        
    def calcCoG(self, frame, area):
        l = area.GetLeft() 
        r = area.GetRight()
        t = area.GetTop()
        b = area.GetBottom()
        gray = cv2.cvtColor(frame[t:b, l:r], cv2.COLOR_BGR2GRAY)#crop and gray
#        return ((l+r)/2, (t+b)/2)
        try:
            if AutoGuideSetup.isThresAuto:
                ret, binImg = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)#binarize by otsu
            else:
                ret, binImg = cv2.threshold(gray, AutoGuideSetup.thresValue, 255, cv2.THRESH_BINARY)#binarize
        
            cnts = cv2.findContours(binImg, 0, 2)[0]
            areas = [cv2.contourArea(cnt) for cnt in cnts] #find max contour
            cnt_max = [cnts[areas.index(max(areas))]][0]
            cog = cv2.moments(cnt_max)#get Center of Gravity
            (cx, cy) = (float(cog["m10"]/cog["m00"]), float(cog["m01"]/cog["m00"]))
            return (cx + l, cy + t)#move origin to original image origin
        except:
            print("Can't calcurate CoG. Return center of frame")
            return ((l+r)/2, (t+b)/2)
            
    def drawGuideStarLocation(self, frame, area, number = -1):
        
        cv2.normalize(frame, frame, 0, 255, cv2.NORM_MINMAX)

        if number < 0:
            for i in len(area):
                l = area[i].GetLeft() 
                r = area[i].GetRight()
                t = area[i].GetTop()
                b = area[i].GetBottom()
                cv2.rectangle(frame, 
                                (l, t), 
                                (r, b), 
                                (255, 0, 0), 1)
        elif number < len(area):
            l = area[number].GetLeft() 
            r = area[number].GetRight()
            t = area[number].GetTop()
            b = area[number].GetBottom()
            cv2.rectangle(frame, 
                            (l, t), 
                            (r, b), 
                            (255, 0, 0), 1)
                            
            cx, cy = self.calcCoG(frame, area[number])
            cv2.circle(frame, (int(cx), int(cy)), 1, (0, 255,0), 1)
        return frame