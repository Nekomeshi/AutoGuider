import wx
import Preview
import threading
import ZoomPreview
import SearchGuideStar
import time
import cv2
import CalibGuideDirection
import GuideCtrl
import GuideError
import AutoGuide
import AutoGuideSetup

STATE_PREV_OFF          = 0
STATE_PREV_ON           = 1
STATE_SEARCH_GUIDE_STAR = 2
STATE_SELECT_GUIDE_STAR = 3
STATE_CALIB_DIRECTION   = 4
STATE_WATING_START_GUIDE = 5
STATE_AUTO_GUIDING      = 6


ERROR_LOST_FRAME             = 0
ERROR_NOT_FOUND_GUIDE_STAR   = 1
ERROR_LOST_GUIDE_STAR        = 2
ERROR_STAGE_OUT_OF_CTRL      = 3
ERROR_INVALID_CTRL_INPUT     = 4

AUTOGUIDE_DIR_LR = 0
AUTOGUIDE_DIR_UD = 1
AUTOGUIDE_DIR_BOTH = 2

    
class AutoGuideCtrlThread(threading.Thread):

    __capture = None
    __sleepTime = None #unit = Sec  not mS
    __state = STATE_PREV_OFF
    __isRunning = False

    __previewFrame = None
    __lockFrame = None
    __lockState = None
    
    __screenWidth = 0
    __screenHeight = 0
    
    __onErrorOccured = None
    __onStateChanged = None
    
    __zoomPreview = None
    __searchGuideStar = None
    __calibGuideDirection = None
    __autoGuide = None
    __guideDir = AUTOGUIDE_DIR_BOTH
    __guideFrameRect = None
    __guideInitArea = None
    
    def __init__(self, 
                capture, 
                screenWidth,
                screenHeight,
                guideCtrl,
                initState = STATE_PREV_OFF, 
                errorCB = None, 
                stateChangeCB = None, 
                fps = 15):
        super(AutoGuideCtrlThread, self).__init__()
        self.__screenWidth = screenWidth
        self.__screenHeight = screenHeight
        
        
        self.__sleepTime  = 1./float(fps)
        self.__capture = capture
        self.__onErrorOccured = errorCB
        self.__onStateChanged = stateChangeCB
        self.__state = initState
        self.__lockFrame = threading.Lock()
        self.__lockState = threading.Lock()
        self.__zoomPreview = ZoomPreview.ZoomPreview(screenWidth, screenHeight)
        self.__searchGuideStar = SearchGuideStar.SearchGuideStar()
        self.__calibGuideDirection = CalibGuideDirection.CalibGuideDirection(guideCtrl)
        self.__autoGuide = AutoGuide.AutoGuide(guideCtrl)
        
    def run(self):
        self.__isRunning = True
        noFrameCounter = -1
        while self.__isRunning:
            tm1 = time.time()
            frm = self.__capture.getFrame()

            if frm == None:
                # don' care lost frame in first 10 frames
                if noFrameCounter < 0:#Lost frame at 1st tiem 
                    noFrameCounter = 5/self.__sleepTime #Set wait counter for 5sec
                elif noFrameCounter == 0:#Lost frame 5sec in a row
                    if self.__onErrorOccured != None:
                        self.__onErrorOccured(self.__state, ERROR_LOST_FRAME)
                else:#still losing frame
                    noFrameCounter = noFrameCounter -1
            else:
                if noFrameCounter >= 0:#reset lost frame counter
                    noFrameCounter = -1
                self.__guideStateMachine(frm)
            tm2 = time.time()
    
            st = max(self.__sleepTime - (tm2 - tm1), 0.01)
            time.sleep(st)
            
    def stop(self, waitEndThread = False):
        self.__isRunning = False
        if waitEndThread:
            self.join()

    def isRunning(self):
        return self.__isRunning
    
    __guideAera = None #data type is wx.Rect
    def __guideStateMachine(self, frame):
        if frame == None:
            self.__previewFrame = None
            if self.__onErrorOccured != None:
                self.__onErrorOccured(self.__state, ERROR_LOST_FRAME)
            self.__lockFrame.acquire()
            self.__previewFrame = None
            self.__lockFrame.release()
            return
        
        self.__lockState.acquire()
        st = self.__state
        self.__lockState.release()
        print("running state = {}".format(st))
        
        if st == STATE_PREV_OFF:
            self.__lockFrame.acquire()
            self.__previewFrame = None
            self.__lockFrame.release()
            return 
        elif st == STATE_PREV_ON:
            self.__lockFrame.acquire()
            self.__previewFrame = self.__zoomPreview.drawPreview(frame) #draw preview
            self.__lockFrame.release()
            return
        elif st == STATE_SEARCH_GUIDE_STAR:
            initArea = self.__zoomPreview.getPreviewArea()#get preview area as initial search area
            guideAreaList = self.__searchGuideStar.searchGuideStarInit(frame, 
                                        self.__screenWidth, 
                                        self.__screenHeight, 
                                        initArea) #guide area is sorted by the area size
            if guideAreaList == None or len(guideAreaList) == 0:
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_NOT_FOUND_GUIDE_STAR)
                self.changeState(STATE_PREV_ON)#return state to STATE_PREV_ON
                return
            
            #set the track frame so that the guide star is at the center
            g = None
            for guideArea in guideAreaList:
                l = guideArea.GetLeft()
                t = guideArea.GetTop()
                r = guideArea.GetRight()
                b = guideArea.GetBottom()
                l = (l+r - self.__screenWidth)/2
                t = (t+b - self.__screenHeight)/2
                h, w = frame.shape[:2]
                if l < 0:
                    l = 0
                elif l+self.__screenWidth >= w:
                    l = w -  self.__screenWidth
                if t < 0:
                    t = 0
                elif  t+self.__screenHeight >= h:
                    t = h - self.__screenHeight
                    
                rect = wx.Rect(l, t, self.__screenWidth, self.__screenHeight)
                g = guideArea
                break
            print("RECT = {}".format(rect))
            if g == None:
                self.__onErrorOccured(self.__state, ERROR_NOT_FOUND_GUIDE_STAR)
                self.changeState(STATE_PREV_ON)#return state to STATE_PREV_ON
                return
            
            self.__guideInitArea = g
            self.__guideInitArea.OffsetXY(- rect.GetLeft(), - rect.GetTop())
            self.__guideFrameRect = rect
            
            print("guide area list = {}".format(guideArea))
            self.__lockFrame.acquire()
            f = frame[t:t+self.__screenHeight, l:l+self.__screenWidth];
            self.__previewFrame = self.__searchGuideStar.drawGuideStarLocation(f, 
                                                                        [self.__guideInitArea], 0)#draw largest area box
            self.__lockFrame.release()
            
            self.changeState(STATE_CALIB_DIRECTION)#switch state to STATE_CALIB_DIRECTION
            
            return
        elif st == STATE_SELECT_GUIDE_STAR:#don't use this state for a while.....
            print("not used so far")
            return
        elif st == STATE_CALIB_DIRECTION:
            #crop frame so that it fits to screen size
            r = self.__guideFrameRect
            croppedFrame = frame[r.GetTop():(r.GetBottom()+1),r.GetLeft():(r.GetRight()+1)]
            h, w = croppedFrame.shape[:2]
            cv2.normalize(croppedFrame, croppedFrame, 0, 255, cv2.NORM_MINMAX)
#            searchFrame = frame[t:b, l:r] 
            try:
                calSTLR = self.__calibGuideDirection.getCalibDirectionState(CalibGuideDirection.CALIB_DIR_LR)
                
                if calSTLR == CalibGuideDirection.CALIB_STATE_COMPLETE:#LR direction is calibrated
                    if self.__guideDir == AUTOGUIDE_DIR_LR:#Not need to calibrate UD
                        self.changeState(STATE_WATING_START_GUIDE)#CalibComplete
                        return
                    calSTUD = self.__calibGuideDirection.getCalibDirectionState(CalibGuideDirection.CALIB_DIR_UD)
                    if calSTUD == CalibGuideDirection.CALIB_STATE_COMPLETE:#Both direction is completed
                        self.changeState(STATE_WATING_START_GUIDE)
                        return
                    elif calSTUD == CalibGuideDirection.CALIB_STATE_NOOP:#UD direction is not started
                        print("initarea = {}".format(self.__guideInitArea))
                        #Shorten calib length because guide vector is orthogonal to Ra. Only sign need to be calculated
                        calibLen = int(min(float(self.__screenWidth), float(self.__screenHeight))/float(AutoGuideSetup.calibLength)*1.5)
                        self.__calibGuideDirection.startCalibDirection(croppedFrame, 
                                                                        self.__guideInitArea, 
                                                                        False, #for UD
                                                                        AutoGuideSetup.searchWindowSizeInit, 
                                                                        calibLen,
                                                                        AutoGuideSetup.ret2OrgPosDec,
                                                                        AutoGuideSetup.isDutyAuto,
                                                                        AutoGuideSetup.dutyAutoMag,
                                                                        AutoGuideSetup.isCalibSpeedHigh,
                                                                        AutoGuideSetup.pwmCapCount)
                    else:
                        self.__calibGuideDirection.setNextFrame(croppedFrame)
                else:#calib LR direction
                    if calSTLR == CalibGuideDirection.CALIB_STATE_NOOP:#calib not started
                        print("initarea = {}".format(self.__guideInitArea))
                        calibLen = min(self.__screenWidth, self.__screenHeight)/AutoGuideSetup.calibLength
                        self.__calibGuideDirection.startCalibDirection(croppedFrame, 
                                                                        self.__guideInitArea, 
                                                                        True, #for LR
                                                                        AutoGuideSetup.searchWindowSizeInit, 
                                                                        calibLen,
                                                                        AutoGuideSetup.ret2OrgPosRa,
                                                                        AutoGuideSetup.isDutyAuto,
                                                                        AutoGuideSetup.dutyAutoMag,
                                                                        AutoGuideSetup.isCalibSpeedHigh,
                                                                        AutoGuideSetup.pwmCapCount)
                    else:
                        self.__calibGuideDirection.setNextFrame(croppedFrame)
                        
            except GuideError.GuideDirectionInvalidInputError:
                self.__calibGuideDirection.reset()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_INVALID_CTRL_INPUT)
                self.changeState(STATE_PREV_ON)#return state to STATE_PREV_ON
                return
            except GuideError.GuideDirectionStarLostError:
                self.__calibGuideDirection.reset()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_LOST_GUIDE_STAR)
                self.changeState(STATE_PREV_ON)#return state to STATE_PREV_ON
                return
            except GuideError.GuideDirectionStarNotFoundError:
                self.__calibGuideDirection.reset()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_NOT_FOUND_GUIDE_STAR)
                self.changeState(STATE_PREV_ON)#return state to STATE_PREV_ON
                return
            except GuideError.GuideDirectionOutOfFrameError:
                self.__calibGuideDirection.reset()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_STAGE_OUT_OF_CTRL)
                self.changeState(STATE_PREV_ON)#return state to STATE_PREV_ON
                return
                
                
                
            #draw calibration process
            self.__lockFrame.acquire()
            self.__previewFrame = \
                self.__calibGuideDirection.drawFrame(croppedFrame)
            self.__lockFrame.release()
            return
        
        elif st == STATE_WATING_START_GUIDE:
            r = self.__guideFrameRect
            croppedFrame = frame[r.GetTop():(r.GetBottom()+1),r.GetLeft():(r.GetRight()+1)]
            cv2.normalize(croppedFrame, croppedFrame, 0, 255, cv2.NORM_MINMAX)
            self.__lockFrame.acquire()
            self.__previewFrame = croppedFrame #draw preview
            self.__lockFrame.release()
            return
        
        elif st == STATE_AUTO_GUIDING:
            r = self.__guideFrameRect
            croppedFrame = frame[r.GetTop():(r.GetBottom()+1),r.GetLeft():(r.GetRight()+1)]
            cv2.normalize(croppedFrame, croppedFrame, 0, 255, cv2.NORM_MINMAX)
            try:
                if not self.__autoGuide.isAutoGuideRunning():
                    duty = [AutoGuideSetup.dutyRa, AutoGuideSetup.dutyDec]
                    if AutoGuideSetup.isDutyAuto:
                        duty = [self.__calibGuideDirection.getGuideDuty(CalibGuideDirection.CALIB_DIR_LR),
                                self.__calibGuideDirection.getGuideDuty(CalibGuideDirection.CALIB_DIR_UD)]
                                
                    self.__autoGuide.startAutoGuide(self.__calibGuideDirection.getGuideDirection(),
                                                    croppedFrame,
                                                    AutoGuideSetup.searchWindowSizeTrack, duty,
                                                    self.__guideDir == AUTOGUIDE_DIR_LR)
                else:
                    self.__autoGuide.setNextFrame(croppedFrame)
            except GuideError.GuideDirectionInvalidInputError:
                self.__autoGuide.stopAutoGuide()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_INVALID_CTRL_INPUT)
                self.changeState(STATE_WATING_START_GUIDE)#return state to STATE_WATING_START_GUIDE
                return
            except GuideError.GuideDirectionStarLostError:
                self.__autoGuide.stopAutoGuide()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_LOST_GUIDE_STAR)
                self.changeState(STATE_WATING_START_GUIDE)#return state to STATE_WATING_START_GUIDE
                return
            except GuideError.GuideDirectionStarNotFoundError:
                self.__autoGuide.stopAutoGuide()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_NOT_FOUND_GUIDE_STAR)
                self.changeState(STATE_WATING_START_GUIDE)#return state to STATE_WATING_START_GUIDE
                return
            except GuideError.GuideDirectionOutOfFrameError:
                self.__autoGuide.stopAutoGuide()
                if self.__onErrorOccured != None:
                    self.__onErrorOccured(self.__state, ERROR_STAGE_OUT_OF_CTRL)
                self.changeState(STATE_WATING_START_GUIDE)#return state to STATE_WATING_START_GUIDE
                return
            #draw guide process
            self.__lockFrame.acquire()
            self.__previewFrame = self.__autoGuide.drawFrame(croppedFrame)
            self.__lockFrame.release()
            return
                
        else:
            print("Invalid state{}".format(self.__state))
        

    def getCurrentState(self):
        return self.__state

    def cancelCalibration(self):
        self.__calibGuideDirection.cancelCalibDirection()
        self.changeState(STATE_PREV_ON)
        
    def changeState(self, newState):
        oldState = -1
        self.__lockState.acquire()
        if self.__state != newState:
            if self.__state == STATE_AUTO_GUIDING:
                self.__autoGuide.stopAutoGuide()
                
            oldState = self.__state
            self.__state = newState
        self.__lockState.release()
        if oldState >= 0 and oldState != newState and self.__onStateChanged != None:
            self.__onStateChanged(oldState, newState)
            
    
    def getPreviewFrame(self):

        self.__lockFrame.acquire()
        frame = self.__previewFrame
        self.__lockFrame.release()
        return frame
    
    def setZoom(self, isEnlarge):
        self.__zoomPreview.setZoom(isEnlarge)
    
    def setShift(self, direction):
        self.__zoomPreview.setShift(direction)
        
    #set guide direction. This method shouldn't be called if state is STATE_CALIB_DIRECTION
    #direction : AUTOGUIDE_DIR_LR ->Ra only
    #            AUTOGUIDE_DIR_BOTH->Both of Ra and Dec
    #return value : True -> Direction already calibrated
    #               False->  not calibrated
    def setGuideDirection(self, dir):
        self.__guideDir = dir
        st = self.__calibGuideDirection.getCalibDirectionState(CalibGuideDirection.CALIB_DIR_LR)
        calibed = (st == CalibGuideDirection.CALIB_STATE_COMPLETE)
        if dir == AUTOGUIDE_DIR_BOTH:
            st = self.__calibGuideDirection.getCalibDirectionState(CalibGuideDirection.CALIB_DIR_UD)
            calibed = calibed and (st == CalibGuideDirection.CALIB_STATE_COMPLETE)
        return calibed
    def getGuideDuty(self):
        if AutoGuideSetup.isDutyAuto:
            return [self.__calibGuideDirection.getGuideDuty(CalibGuideDirection.CALIB_DIR_LR),
                    self.__calibGuideDirection.getGuideDuty(CalibGuideDirection.CALIB_DIR_UD)]
        else:
            return [AutoGuideSetup.dutyRa, AutoGuideSetup.dutyDec]
        
    def resetGuideCalibDirection(self):
        self.__calibGuideDirection.reset()
        