import wx
import cv2
import SearchGuideStar
import numpy
import GuideError
import AutoGuideSetup

class AutoGuide:
    __guideCtrl = None
    __searchStar = None
    __isLROnly = False
    __guideDirection = None
    __isGuideStarted = False
    __tolerance = 0
    __initPos = None
    __curPos = None

    __isGuideStarted = False
    __isOrgGuideSpeedHigh = False
    __guideDuty = [100, 100]
    
    def __init__(self, guideCtrl):
        self.__guideCtrl = guideCtrl
        self.__searchStar = SearchGuideStar.SearchGuideStar()

    def isAutoGuideRunning(self):
        return self.__isGuideStarted

    def stopAutoGuide(self):
        if self.__isGuideStarted:
            self.__guideCtrl.stopAll()
            self.__guideCtrl.ctrlSpeed(self.__isOrgGuideSpeedHigh)#reset to original speed
            self.__isGuideStarted = False
            
    def startAutoGuide(self, guideDirection, frame, tolerance, duty, isLROnly = False):
        self.stopAutoGuide()
        self.__guideDuty = duty
        
        if not self.__guideCtrl.isInputRPi():
            raise GuideError.GuideDirectionInvalidInputError("Should be switched to RPi")
            return
            
        starList = self.__searchStar.searchGuideStar(frame)
        
        if starList == None or len(starList) == 0:
            raise GuideError.GuideDirectionStarNotFoundError("No guide star found")
            return
        
        cx, cy = self.__searchStar.calcCoG(frame, starList[0])#get Center of gravity of guide star
        self.__initPos = (cx, cy)
        self.__curPos = (cx, cy)

        self.__isLROnly = isLROnly
        self.__guideDirection = guideDirection
        print("Guide Direction = {}".format(guideDirection))
        
        self.__tolerance = tolerance
        
        print("is High Speed? {}".format(self.__guideCtrl.isHighSpeed()))
        
        self.__isOrgGuideSpeedHigh = self.__guideCtrl.isHighSpeed()
        if self.__isOrgGuideSpeedHigh == True:
            self.__guideCtrl.ctrlSpeed(False)#set speed to low if it is originaly high speed

        self.__isGuideStarted  = True
    
    def setNextFrame(self, frame):
        #create new search area based last star pos
        h, w = frame.shape[:2]
        print("current pos  = {}".format(self.__curPos))
        area = wx.Rect(self.__curPos[0] - self.__tolerance, 
                        self.__curPos[1] - self.__tolerance, 
                        self.__tolerance*2+1, 
                        self.__tolerance*2+1)
        wholeArea = wx.Rect(0, 0, w, h)
        if not wholeArea.ContainsRect(area):#if out of frame
            self.__guideCtrl.stopAll()
            raise GuideError.GuideDirectionOutOfFrameError("Star is out of frame({})".format(self.__curPos))
            return False
        
        #find new position
        starList = self.__searchStar.searchGuideStar(frame, area)
        if starList == None or len(starList) == 0:
            self.__guideCtrl.stopAll()
            raise GuideError.GuideDirectionStarLostError("No guide star found")
            return False

        
        #get CoG
        cx, cy = self.__searchStar.calcCoG(frame, starList[0])
        print("StarList = {}, area = {} cxcy = {} {}".format(starList[0], area, cx, cy))
        #update current pos for next frame search
        self.__curPos = (cx, cy)

        vec = numpy.array([float(cx - self.__initPos[0]), float(cy - self.__initPos[1])])
        dist = numpy.linalg.norm(vec)
        print("Vec = {} dist = {}".format(vec, dist))
        if dist < 0.01:#guide star is at the center. Do not need to move motor.
            self.__guideCtrl.stopAll()
            return True

        ra = numpy.dot(vec, self.__guideDirection[0])
        pwm = abs(round(ra*self.__guideDuty[0]))
        if pwm > 100:
            pwm = 100
        if ra > 0:
            self.__guideCtrl.toRaMinus(pwm)
        elif ra < 0:
            self.__guideCtrl.toRaPlus(pwm)
        else:
            self.__guideCtrl.stopRa()
            
        if self.__isLROnly:
            return True
        
        dec = numpy.dot(vec, self.__guideDirection[1])
        pwm = abs(round(dec*self.__guideDuty[1]))
        if dec > 0:
            self.__guideCtrl.toDecMinus(pwm)
        elif dec < 0:
            self.__guideCtrl.toDecPlus(pwm)
        else:
            self.__guideCtrl.stopDec()
        return True

    def drawFrame(self, frame):
        if frame == None:
            print("Frame is None")
            return None
        f = frame.copy()
        
        if self.__initPos == None or self.__guideDirection == None:
            return f
        
        ipx = int(self.__initPos[0])
        ipy = int(self.__initPos[1])

        vec =  self.__guideDirection[0]
        #draw guide vector
        cv2.line(f, 
                (ipx, ipy), (ipx + int(vec[0]*20.0), ipy + int(vec[1]*20.0)),
                (255, 255, 0), 1)
        if not self.__isLROnly:
            vec =  self.__guideDirection[1]
            cv2.line(f, 
                     (ipx, ipy), (ipx + int(vec[0]*20.0), ipy + int(vec[1]*20.0)),
                     (255, 0, 255), 1)
        #draw initial pos
        cv2.circle(f, (ipx, ipy), 1, (0, 255,0), 1)
        
        #draw current pos
        if self.__curPos == None:
            return f
        
        cpx = int(self.__curPos[0])
        cpy = int(self.__curPos[1])
        cv2.circle(f, (cpx, cpy), 1, (255, 0, 255), 1)
        cv2.rectangle(f, #draw initial pos
                            (cpx - self.__tolerance, cpy - self.__tolerance), 
                            (cpx + self.__tolerance, cpy + self.__tolerance), 
                            (255, 0, 255), 1)

        return f
    