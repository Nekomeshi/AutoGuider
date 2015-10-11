import wx
import cv2
import SearchGuideStar
import numpy
import GuideError

CALIB_STATE_NOOP = 0
CALIB_STATE_STARTED = 1
CALIB_STATE_DUTY = 2
CALIB_STATE_RETURNING = 3
CALIB_STATE_COMPLETE = 4

CALIB_DIR_LR = 0
CALIB_DIR_UD = 1
CALIB_DIR_BOTH = 2

class CalibGuideDirection:
    __guideCtrl = None
    __searchStar = None
    
    __isOrgGuideSpeedHigh = False

    __calibDir = CALIB_DIR_LR
    
    __initPos = [None,None]
    __lastPos = None
    __curPos = None
    __vecFromInitPos = [None,None]

    
    __tolerance = 0
    __endDist = 0
    __calibState = [CALIB_STATE_NOOP, CALIB_STATE_NOOP]
    __returnToOrgPos = True
    __frameStep = numpy.array([])
    __dutyPWM = [-1, -1]
    __calibDuty = False
    __dutyMag = 1
    __pwmCapCount = 5
    
    def __init__(self, guideCtrl):
        self.__guideCtrl = guideCtrl
        self.__searchStar = SearchGuideStar.SearchGuideStar()
        self.reset()
        
    def reset(self):
        self.__initPos = [None,None]
        self.__curPos = None
        self.__lastPos = None
        self.__vecFromInitPos = [None,None]
        self.__calibState = [CALIB_STATE_NOOP, CALIB_STATE_NOOP]

    
    def cancelCalibDirection(self):
        self.__stopMotor()
        self.reset()
        
    #Start calibrate direction
    #initArea: wx.Rect for searching star. If it is None, whole area of frame is used
    #isLR: Axis to calibrate True:L-R (Ra) False:U-D(Dec)
    #tolerance: On next frame, CoG +/- this value will be the next search area
    #endDistance: Distance from initial CoG to complete this calibration
    def startCalibDirection(self, frame, initArea, isLR, tolerance, 
                            endDistance, return2OrgPos, calibDuty, 
                            dutyMag, isCalibSpeedHigh, pwmCapCount):
        #check input SW
        if not self.__guideCtrl.isInputRPi():
            raise GuideError.GuideDirectionInvalidInputError("Should be switched to RPi")
            return
        l = (initArea.GetLeft() + initArea.GetRight())/2 - tolerance
        t = (initArea.GetTop() + initArea.GetBottom())/2 - tolerance
        ia = wx.Rect(l, t, tolerance*2,tolerance*2) 
        starList = self.__searchStar.searchGuideStar(frame, ia)
        if starList == None or len(starList) == 0:
            raise GuideError.GuideDirectionStarNotFoundError("No guide star found")
            return
        if isLR:
            self.__calibDir = CALIB_DIR_LR
        else:
            self.__calibDir = CALIB_DIR_UD
            
        cx, cy = self.__searchStar.calcCoG(frame, starList[0])#get Center of gravity of guide star
        self.__initPos[self.__calibDir] = (cx, cy)
        self.__curPos = (cx, cy)
        
        print("starList = {}  InitPos = {}, {} {}".format(starList[0], cx, cy, initArea))
        
        #backup the original guide speed 
        self.__isOrgGuideSpeedHigh = self.__guideCtrl.isHighSpeed()
        if self.__isOrgGuideSpeedHigh != isCalibSpeedHigh:
            self.__guideCtrl.ctrlSpeed(isCalibSpeedHigh)#set Calib Motor Speed
        
        self.__tolerance = tolerance
        self.__endDist = endDistance
        self.__returnToOrgPos = return2OrgPos
        
        if self.__isLR():
            self.__guideCtrl.toRaPlus(100)            
        else:#start Dec motor
            self.__guideCtrl.toDecPlus(100)
        
        self.__calibDuty = calibDuty
        self.__dutyMag = dutyMag
        self.__pwmCapCount = pwmCapCount
        
        self.__calibState[self.__calibDir] = CALIB_STATE_STARTED

    def __isLR(self):
        return self.__calibDir == CALIB_DIR_LR
    
    def __stopMotor(self):
        self.__guideCtrl.stopAll()
        self.__guideCtrl.ctrlSpeed(self.__isOrgGuideSpeedHigh)#reset to original speed
        
    def setNextFrame(self, frame):
        print("CalibState = {}".format(self.__calibState[self.__calibDir]))
        
        #check input SW
        if not self.__guideCtrl.isInputRPi():
            self.__stopMotor()
            raise GuideError.GuideDirectionInvalidInputError("Should be switched to RPi")
            return False
        #create new search area based last star pos
        h, w = frame.shape[:2]
        print("self.__curPos = {}".format(self.__curPos))
        tole = self.__tolerance
        area = wx.Rect(self.__curPos[0] - tole, self.__curPos[1] - tole, tole*2+1, tole*2+1)
        wholeArea = wx.Rect(0, 0, w, h)
        if not wholeArea.ContainsRect(area):#if out of frame
            self.__stopMotor()
            raise GuideError.GuideDirectionOutOfFrameError("Star is out of frame({}, {}".format(self.__curPos[0], self.__curPos[1]))
            return False
        
        #find new position
        starList = self.__searchStar.searchGuideStar(frame, area)
        if starList == None or len(starList) == 0:
            self.__stopMotor()
            raise GuideError.GuideDirectionStarLostError("No guide star found")
            return False

        
        #get CoG
        cx, cy = self.__searchStar.calcCoG(frame, starList[0])

        print("StarList = {}, area = {} cxcy = {} {}".format(starList[0], area, cx, cy))
        #update current pos
        self.__lastPos = self.__curPos
        self.__curPos = (cx, cy)
        print("curpos ={}".format(self.__curPos))
        ip = self.__initPos[self.__calibDir]
        if ip == None:
            return False
        
        vec = numpy.array([float(cx - ip[0]), float(cy - ip[1])])
        dist = numpy.linalg.norm(vec)
        print("Vec = {}, dist = {}".format(vec, dist))
        if self.__calibState[self.__calibDir] == CALIB_STATE_STARTED:#now calibrating

            if self.__isLR():#return Ra/Dec motor to initial pos
                if dist < self.__endDist:#calib not completed
                    self.__vecFromInitPos[self.__calibDir] = vec #store this value for drawing vector
                else:#calib completed
                    self.__vecFromInitPos[self.__calibDir] = vec/dist#normalize the vector
                    if self.__calibDuty:
                        self.__startDuty();
                    else:
                        self.__dutyPWM[self.__calibDir] = -1
                        self.__startReturn();
            else:
                self.__vecFromInitPos[self.__calibDir] = [float(self.__vecFromInitPos[CALIB_DIR_LR][1]),
                                                        float(-self.__vecFromInitPos[CALIB_DIR_LR][0])] #vec of Dec is prependiculer to Ra
                sz = numpy.dot(self.__vecFromInitPos[self.__calibDir], vec); #Ra vec is normalized
                if sz < 0.0:
                    self.__vecFromInitPos[self.__calibDir] = [float(-self.__vecFromInitPos[CALIB_DIR_LR][1]),
                                                            float(self.__vecFromInitPos[CALIB_DIR_LR][0])]
                    sz = sz * -1.0
                if sz >= self.__endDist:
                    if self.__calibDuty:
                        self.__startDuty();
                    else:
                        self.__dutyPWM[self.__calibDir] = -1
                        self.__startReturn();
            
            print("Vector{} = {}".format(self.__calibDir, self.__vecFromInitPos[self.__calibDir]))

            return True
        elif self.__calibState[self.__calibDir] == CALIB_STATE_DUTY:
            vec =  numpy.array([float(self.__curPos[0] - self.__lastPos[0]), 
                                float(self.__curPos[1] - self.__lastPos[1])])
            #calc shift value per 1 frame. unit is pixel
            v = numpy.dot(vec, self.__vecFromInitPos[self.__calibDir])
            if v <= 0: #don't use this value because direction is invalid
                return True
            
            self.__frameStep = numpy.append(self.__frameStep, v)

            if len(self.__frameStep) > self.__pwmCapCount:
                #chose median and calc duty so that shift per 1 frame is 1 pixel
                #duty is between 1 to 100. 100 means full speed.
                
                duty = int(round(100.0*float(self.__dutyMag)/numpy.median(self.__frameStep)))
                if duty < 1:
                    duty = 1
                elif duty > 100:
                    duty = 100
                self.__dutyPWM[self.__calibDir] = duty            
                self.__startReturn();

            return True
        elif self.__calibState[self.__calibDir] == CALIB_STATE_RETURNING:#now returning

            vec = vec/dist#normalize the vector]
            if numpy.dot(vec, self.__vecFromInitPos[self.__calibDir]) < 0.01 :#if returned to almost initial position or already passed
                #Stop motor
                self.__stopMotor()
                self.__calibState[self.__calibDir] = CALIB_STATE_COMPLETE
            return True

        self.__stopMotor()
        raise Exception("Invalid calib status {}".format(self.__calibState))
        return False
    
    def __startDuty(self):
        self.__guideCtrl.ctrlSpeed(False)#set to LOW speed
        self.__frameStep = numpy.array([])
        self.__calibState[self.__calibDir] = CALIB_STATE_DUTY
    
    def __startReturn(self):
        if not self.__returnToOrgPos:
            self.__stopMotor()
            self.__calibState[self.__calibDir] = CALIB_STATE_COMPLETE
        else:
            if self.__isLR():
                self.__guideCtrl.ctrlSpeed(False)#set to Low speed to avoid backlash
                self.__guideCtrl.toRaMinus(100)
            else:
                self.__guideCtrl.toDecMinus(100)
                self.__guideCtrl.ctrlSpeed(True)#set to High speed to return quickly
                
            self.__calibState[self.__calibDir] = CALIB_STATE_RETURNING
        
    
    def drawFrame(self, frame):
        f = frame.copy()
        for i in range(len(self.__vecFromInitPos)):
            state = self.__calibState[i]
            if self.__initPos[i] != None and self.__vecFromInitPos[i] != None:
                ipx = int(self.__initPos[i][0])
                ipy = int(self.__initPos[i][1])
                vec = self.__vecFromInitPos[i]
                #draw initial pos
                cv2.circle(f, (ipx, ipy), 1, (0, 255,0), 1)

                if state == CALIB_STATE_DUTY or \
                    state == CALIB_STATE_COMPLETE or \
                    state == CALIB_STATE_RETURNING:#normalized vector is calcurated
                    if i == CALIB_DIR_LR:
                        cv2.line(f, 
                                (ipx, ipy), (ipx + int(vec[0]*50.0), ipy + int(vec[1]*50.0)),
                                (255, 255, 0), 1)
                    else:
                        cv2.line(f, 
                                (ipx, ipy), (ipx + int(vec[0]*50.0), ipy + int(vec[1]*50.0)),
                                (255, 0, 255), 1)
        if self.__curPos != None and self.__initPos[self.__calibDir] != None:#draw current pos
            ipx = int(self.__initPos[self.__calibDir][0])
            ipy = int(self.__initPos[self.__calibDir][1])
            cpx = int(self.__curPos[0])
            cpy = int(self.__curPos[1])
            if self.__calibState[self.__calibDir] == CALIB_STATE_STARTED:#now calibrating
                cv2.line(f, 
                        (ipx, ipy), (cpx, cpy),
                        (255, 0, 0), 1)
            rectcolor = (255, 0, 0)
            if self.__calibState[self.__calibDir] == CALIB_STATE_DUTY:
                rectcolor = (0, 255, 0)
            elif self.__calibState[self.__calibDir] == CALIB_STATE_RETURNING:
                rectcolor = (0, 0, 255)

            cv2.rectangle(f, 
                    (cpx - self.__tolerance, cpy - self.__tolerance), 
                    (cpx + self.__tolerance, cpy + self.__tolerance), 
                    rectcolor, 1)
        return f
    def getGuideDirection(self):
        return self.__vecFromInitPos
    
    def getCalibDirectionState(self, dir):
        return self.__calibState[dir]
    
    def getGuideDuty(self, dir):
        return self.__dutyPWM[dir]
    