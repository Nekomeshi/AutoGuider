import wx
import Preview
import V4L2Ctrl
import GuideCtrl
import threading
import ZoomDialog
import ZoomPreview
import AutoGuideCtrlThread
import Capture
import CalibDialog
import AutoGuideSetup

BTN_START_CAMERA =  "CAMERA"
BTN_START_CALIB =   "CALIB"
BTN_START_GUIDE =   "GUIDE"
BTN_ZOOM =          "ZOOM"
BTN_AXIS =          "AXIS"
BTN_GUIDE_CTRL =    "GUIDE_CTRL"
LBL_GUIDE_READY =   "GUIDE_READY"
LBL_DUTY_AUTO =     "GUIDE_DUTY_AUTO"
LBL_DUTY_RA =       "GUIDE_DUTY_RA"
LBL_DUTY_DEC=       "GUIDE_DUTY_DEC"

class AutoGuideCtrl(Preview.IPreview):
    
    __capture = None
    __autoGuideThread = None
    __guideCtrl = None
    __v4l2 = None
    __prevWindow = None
    __buttons = None
    __width = 0
    __height = 0
    __fps = 0
    __parentWindow = None
    __calibDialog = None
    __guideStatus = AutoGuideCtrlThread.STATE_PREV_OFF
    
    def __init__(self, parent, guideCtrl, v4l2, prevWindow, buttons):
        self.__parentWindow = parent
        self.__guideCtrl = guideCtrl
        self.__v4l2 = v4l2
        self.__prevWindow = prevWindow
        self.__buttons = buttons
        
        self.__setBind(buttons)
        
        prevButton = buttons.get(BTN_START_CAMERA)
        prevButton.SetValue(False)
        
        try:
            self.__startCapture()
            print("OK init")
            self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_PREV_ON)
            self.__prevWindow.startPreview(self, 5)       
        except Exception, e:
            self.__showErrorMsg("Error", "{}".format(e))
            self.__guideStatus = AutoGuideCtrlThread.STATE_PREV_OFF
            self.__setGuideCtrlButtanState()
            self.__buttons.get(BTN_START_CAMERA).Disable()
            return
    
            
    def __del__(self):
        self.stopCapture()
        
    def __setBind(self, buttons):
        buttons.get(BTN_START_CAMERA).Bind(wx.EVT_TOGGLEBUTTON, self.__onPreviewButtonClicked)
        buttons.get(BTN_ZOOM).Bind(wx.EVT_BUTTON, self.__onZoomButtonClicked)
        buttons.get(BTN_START_CALIB).Bind(wx.EVT_BUTTON, self.__onCalibButtonClicked)
        buttons.get(BTN_START_GUIDE).Bind(wx.EVT_BUTTON, self.__onAutoGuideButtonClicked)

    def __showErrorMsg(self, title, message):
        dlg = wx.MessageDialog(self.__parentWindow, 
                                    message, 
                                    title, 
                                    wx.OK | wx.ICON_EXCLAMATION)
        dlg.ShowModal()


    #button callback
    def __onZoomCtrlButtonClicked(self, event):
        id = event.GetId()
        print("ID = {}".format(id))
        if id == ZoomDialog.BUTTON_OK:
            self.__ZoomDlg.Close()
        elif id == ZoomDialog.BUTTON_ZOOMUP:
            self.__autoGuideThread.setZoom(True)
        elif id == ZoomDialog.BUTTON_ZOOMDOWN:
            self.__autoGuideThread.setZoom(False)
        elif id == ZoomDialog.BUTTON_UP:
            self.__autoGuideThread.setShift(ZoomPreview.SHIFT_UP)
        elif id == ZoomDialog.BUTTON_DOWN:
            self.__autoGuideThread.setShift(ZoomPreview.SHIFT_DOWN)
        elif id == ZoomDialog.BUTTON_LEFT:
            self.__autoGuideThread.setShift(ZoomPreview.SHIFT_LEFT)
        elif id == ZoomDialog.BUTTON_RIGHT:
            self.__autoGuideThread.setShift(ZoomPreview.SHIFT_RIGHT)
            
            
    def __onZoomButtonClicked(self, event):
        sz = self.__parentWindow.GetClientSize()
        y = sz[1] - ZoomDialog.DIALOG_SIZE [1]-1

        self.__ZoomDlg = ZoomDialog.ZoomDialog(self.__parentWindow, 
                                                pos = (0, y))
        self.__ZoomDlg.buttonUp.Bind(wx.EVT_BUTTON, 
                                    self.__onZoomCtrlButtonClicked)
        self.__ZoomDlg.buttonDown.Bind(wx.EVT_BUTTON, 
                                    self.__onZoomCtrlButtonClicked)
        self.__ZoomDlg.buttonLeft.Bind(wx.EVT_BUTTON, 
                                    self.__onZoomCtrlButtonClicked)
        self.__ZoomDlg.buttonRight.Bind(wx.EVT_BUTTON, 
                                    self.__onZoomCtrlButtonClicked)
        self.__ZoomDlg.bitmapButtonOK.Bind(wx.EVT_BUTTON, 
                                    self.__onZoomCtrlButtonClicked)
        self.__ZoomDlg.bitmapButtonZoomUp.Bind(wx.EVT_BUTTON, 
                                    self.__onZoomCtrlButtonClicked)
        self.__ZoomDlg.bitmapButtonZoomDown.Bind(wx.EVT_BUTTON, 
                                    self.__onZoomCtrlButtonClicked)
        self.__ZoomDlg.ShowModal()

    
    def __onPreviewButtonClicked(self, event):
        prevButton = self.__buttons.get(BTN_START_CAMERA)
        print("state = {}".format(prevButton.GetValue()))
        if prevButton.GetValue():
            self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_PREV_ON)
        else:
            self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_PREV_OFF)
            
    def __onCalibButtonClicked(self, event):
        if not self.__guideCtrl.isInputRPi():
            dlg = wx.MessageDialog(self.__parentWindow, 
                                    "Set input to RPi", 
                                    "Error", 
                                    wx.OK | wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            return
        #set guide direction to both of Ra and Dec
        if self.__buttons.get(BTN_AXIS).GetValue():
            dir = AutoGuideCtrlThread.AUTOGUIDE_DIR_BOTH
        else:
            dir = AutoGuideCtrlThread.AUTOGUIDE_DIR_LR
            
        if self.__autoGuideThread.setGuideDirection(dir):#Calibration is already done?
            dlg = wx.MessageDialog(self.__parentWindow, 
                                    "Reset the diurnal motion direction data?", 
                                    "Diurnal motion direction data exists", 
                                    wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() != wx.ID_YES:
                self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_WATING_START_GUIDE)
                return
            else:
                self.__autoGuideThread.resetGuideCalibDirection()
                
        self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_SEARCH_GUIDE_STAR)
            
    def __onAutoGuideButtonClicked(self, event):
        if not self.__guideCtrl.isInputRPi():
            dlg = wx.MessageDialog(self.__parentWindow, 
                                    "Set input to RPi", 
                                    "Error", 
                                    wx.OK | wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            return
        if AutoGuideSetup.isDutyAuto:
            duty = self.__autoGuideThread.getGuideDuty()
            if duty[0] < 0 or duty[1] < 0:
                dlg = wx.MessageDialog(self.__parentWindow, 
                                    "Need to calib again", 
                                    "Error", 
                                    wx.OK | wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                return
                
        self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_AUTO_GUIDING)
        
        
    def __onErrorAutoGuideInMainThread(self, state, errorMsg):
        if errorMsg == AutoGuideCtrlThread.ERROR_LOST_FRAME: #if no frame found, move to STATE_PREV_OFF on any status
            self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_PREV_OFF)
            self.__showErrorMsg("Error", "Can not detect video signal")
            return
        if state == AutoGuideCtrlThread.STATE_SEARCH_GUIDE_STAR or \
            state == AutoGuideCtrlThread.STATE_SELECT_GUIDE_STAR or\
            state == AutoGuideCtrlThread.STATE_CALIB_DIRECTION or\
            state == AutoGuideCtrlThread.STATE_AUTO_GUIDING:
            self.__closeCalibDialog()
            if errorMsg == AutoGuideCtrlThread.ERROR_NOT_FOUND_GUIDE_STAR:
                self.__showErrorMsg("Error", "Can not find guide star")
                return
            if errorMsg == AutoGuideCtrlThread.ERROR_LOST_GUIDE_STAR:
                self.__showErrorMsg("Error", "Guide star lost")
                return
            if errorMsg == AutoGuideCtrlThread.ERROR_STAGE_OUT_OF_CTRL:
                self.__showErrorMsg("Error", "Stage is out of cntrol")
                return
            if errorMsg == AutoGuideCtrlThread.ERROR_INVALID_CTRL_INPUT:
                self.__showErrorMsg("Error", "Turn input SW to RPi")
                return
        
        
        
    def __onErrorAutoGuide(self, state, errorMsg):
        print("onErrorAutoGuide state = {} / meg = {}".format(state, errorMsg))
        wx.CallAfter(self.__onErrorAutoGuideInMainThread, state, errorMsg)
            
    def __setGuideCtrlButtanState(self):
        state = self.__guideStatus
        btnStartCamera = self.__buttons.get(BTN_START_CAMERA)
        btnZoom = self.__buttons.get(BTN_ZOOM)
        btnCalib = self.__buttons.get(BTN_START_CALIB)
        btnGuid = self.__buttons.get(BTN_START_GUIDE)
        btnAxis = self.__buttons.get(BTN_AXIS)
        btnGuideCtrl = self.__buttons.get(BTN_GUIDE_CTRL)
        lblGuideReady = self.__buttons.get(LBL_GUIDE_READY)
        lblIsDutyAuto = self.__buttons.get(LBL_DUTY_AUTO)
        lblDutyRa = self.__buttons.get(LBL_DUTY_RA)
        lblDutyDec = self.__buttons.get(LBL_DUTY_DEC)
        
        if state == AutoGuideCtrlThread.STATE_PREV_OFF:
            btnStartCamera.Enable()
            btnZoom.Disable()
            btnCalib.Disable()
            btnGuid.Disable()
            btnAxis.Enable()
            btnGuideCtrl.Enable()
            lblGuideReady.Disable()
            return
        if state == AutoGuideCtrlThread.STATE_PREV_ON:
            btnStartCamera.Enable()
            btnZoom.Enable()
            btnCalib.Enable()
            btnGuid.Disable()
            btnAxis.Enable()
            btnGuideCtrl.Enable()
            lblGuideReady.Disable()
            return
        if state == AutoGuideCtrlThread.STATE_WATING_START_GUIDE:
            btnStartCamera.Enable()
            btnZoom.Disable()
            btnCalib.Enable()
            btnGuid.Enable()
            btnAxis.Disable()
            btnGuideCtrl.Enable()
            lblGuideReady.Enable()
            duty = [AutoGuideSetup.dutyRa, AutoGuideSetup.dutyDec]
            if AutoGuideSetup.isDutyAuto:
                lblIsDutyAuto.SetLabel("Duty:A")
                duty = self.__autoGuideThread.getGuideDuty()
            else:
                lblIsDutyAuto.SetLabel("Duty:M")
            lblDutyRa.SetLabel("Ra:" + str(duty[0]))
            lblDutyDec.SetLabel("Dec:" + str(duty[1]))

            return
        
    
        
    def __onStateChangedInMainThread(self, oldState, newState):
        self.__guideStatus = newState
        
        self.__setGuideCtrlButtanState()
        
        if newState == AutoGuideCtrlThread.STATE_PREV_OFF:
            prevButton = self.__buttons.get(BTN_START_CAMERA)
            prevButton.SetValue(False)
            self.__closeCalibDialog()
            return
        elif newState == AutoGuideCtrlThread.STATE_PREV_ON:
            prevButton = self.__buttons.get(BTN_START_CAMERA)
            prevButton.SetValue(True)
            return
        elif newState == AutoGuideCtrlThread.STATE_SEARCH_GUIDE_STAR:
            self.__openCalibDialog(AutoGuideCtrlThread.STATE_SEARCH_GUIDE_STAR)
        elif newState == AutoGuideCtrlThread.STATE_SELECT_GUIDE_STAR:
            self.__openCalibDialog(AutoGuideCtrlThread.STATE_SELECT_GUIDE_STAR)
        elif newState == AutoGuideCtrlThread.STATE_CALIB_DIRECTION:
            self.__openCalibDialog(AutoGuideCtrlThread.STATE_CALIB_DIRECTION)
        elif newState == AutoGuideCtrlThread.STATE_WATING_START_GUIDE:
            self.__closeCalibDialog()
        elif newState == AutoGuideCtrlThread.STATE_AUTO_GUIDING:
            self.__openCalibDialog(AutoGuideCtrlThread.STATE_AUTO_GUIDING)

            return
        
    def __onStateChanged(self, oldState, newState):
        print("onStateChanged old state: {} -> new state: {}".format(oldState, newState))
        if oldState == newState:
            return
        wx.CallAfter(self.__onStateChangedInMainThread, oldState, newState)
        
    def __closeCalibDialog(self):
        if self.__calibDialog == None:
            return
        self.__calibDialog.Close()
        del self.__calibDialog
        self.__calibDialog = None

    def __onCalibDialogButtonClicked(self, event):
        if event.GetId() == CalibDialog.BUTTON_CANCEL:
            print("Current Status = {}".format(self.__guideStatus))
            
            self.__closeCalibDialog()
            if self.__guideStatus == AutoGuideCtrlThread.STATE_SEARCH_GUIDE_STAR or \
                self.__guideStatus == AutoGuideCtrlThread.STATE_SELECT_GUIDE_STAR or \
                self.__guideStatus == AutoGuideCtrlThread.STATE_CALIB_DIRECTION:
                
                self.__autoGuideThread.cancelCalibration()
                
            elif self.__guideStatus == AutoGuideCtrlThread.STATE_AUTO_GUIDING:
                self.__autoGuideThread.changeState(AutoGuideCtrlThread.STATE_WATING_START_GUIDE)

            dlg = wx.MessageDialog(self.__parentWindow, 
                                    "Cancelled", 
                                    "cancel", 
                                    wx.OK | wx.ICON_EXCLAMATION)

            return
            
    def __openCalibDialog(self, state):
        if self.__calibDialog != None:
            self.__closeCalibDialog()

        sz = self.__parentWindow.GetClientSize()
        y = sz[1] - CalibDialog.DIALOG_SIZE[1]-1
        self.__calibDialog = CalibDialog.CalibDialog(self.__parentWindow, pos = (0, y))
        if state == AutoGuideCtrlThread.STATE_SEARCH_GUIDE_STAR:
            self.__calibDialog.labelMsg.SetLabel("Now Searching star")
            self.__calibDialog.buttonCancel.Disable()
            self.__calibDialog.buttonBack.Disable()
            self.__calibDialog.buttonNext.Disable()
        elif state == AutoGuideCtrlThread.STATE_SELECT_GUIDE_STAR:
            self.__calibDialog.buttonCancel.Bind(wx.EVT_BUTTON, 
                                            self.__onCalibDialogButtonClicked)
            self.__calibDialog.buttonBack.Bind(wx.EVT_BUTTON, 
                                            self.__onCalibDialogButtonClicked)
            self.__calibDialog.buttonNext.Bind(wx.EVT_BUTTON, 
                                            self.__onCalibDialogButtonClicked)
            self.__calibDialog.labelMsg.SetLabel("Choose star")
        elif state == AutoGuideCtrlThread.STATE_CALIB_DIRECTION:
            self.__calibDialog.labelMsg.SetLabel("Now Calibrating")
            self.__calibDialog.buttonBack.Disable()
            self.__calibDialog.buttonNext.Disable()
            self.__calibDialog.buttonCancel.Bind(wx.EVT_BUTTON, 
                                            self.__onCalibDialogButtonClicked)
        elif state == AutoGuideCtrlThread.STATE_AUTO_GUIDING:
            self.__calibDialog.labelMsg.SetLabel("Now Guiding")
            self.__calibDialog.buttonBack.Disable()
            self.__calibDialog.buttonNext.Disable()
            self.__calibDialog.buttonCancel.Bind(wx.EVT_BUTTON, 
                                            self.__onCalibDialogButtonClicked)
        else:
            print("Invlid state {} for Open Calib Dialog".format(state))
            self.__calibDialog = None
            return
        
        self.__calibDialog.reFitSize()
        self.__calibDialog.ShowModal()

    def getGuideDuty(self):
        if self.__autoGuideThread == None:
            return [-1, -1]
        
        return self.__autoGuideThread.getGuideDuty()

    #capture        
    def __startCapture(self):
        
        if self.__capture != None:#stop capture if running
            self.__stopCapture()

        fmtIndex = self.__v4l2.getAvailableFormatIndexKeys()
        if len(fmtIndex) == 0:
            raise Exception("Invalid Camera Format")
            return False
        fmtList = self.__v4l2.getAvailableFormat(fmtIndex[0])
        if len(fmtList) == 0:
            raise Exception("Invalid Camera Format")
            return False
        
        #format is sorted by resolution size
        #set largest format first
        if AutoGuideSetup.currentResolution == None:
            raise Exception("Select correct camera resolution")
            return False
            
        w, h = AutoGuideSetup.currentResolution
        isFound = False
        for fmt in fmtList:
            ww = fmt.get(V4L2Ctrl.FMT_WIDTH)
            hh = fmt.get(V4L2Ctrl.FMT_HEIGHT)
            if ww == w and hh == h:
                isFound = True
                break;
        if not isFound:
            raise Exception("Select correct camera resolution")
            return False
            
        if AutoGuideSetup.resizeResolution:
            cap = Capture.Capture(0, w, h, fmtList[0].get(V4L2Ctrl.FMT_WIDTH), fmtList[0].get(V4L2Ctrl.FMT_HEIGHT), True)
        else:
            cap = Capture.Capture(0, w, h, captureOnAnotherThread = True)
        if not cap.isCameraAvailable():
            raise Exception("Camera is not available")
            return False
        
        self.__capture = cap
        self.__width = w
        self.__height = h
#        self.__fps = f
        self.__fps = 4 #7.5fps is too fast
        print("Image format = {} x {}, {}fps".format(w, h, self.__fps))
        
        #Start AutoGuide Thread
        
        #get size of display area
        prevSize = self.__prevWindow.GetSize()
        self.__autoGuideThread = AutoGuideCtrlThread.AutoGuideCtrlThread(
                                    self.__capture,
                                    prevSize[0],#width
                                    prevSize[1],#height
                                    self.__guideCtrl,
                                    errorCB = self.__onErrorAutoGuide,
                                    stateChangeCB = self.__onStateChanged,
#                                    fps = 1)
                                    fps = self.__fps)
        self.__autoGuideThread.start()
        
        #Start Capture
        if not self.__capture.startCapture(self.__fps):
            self.__stopCapture()#stop AutoGuidethread in stopCapture()
            raise Exception("Can not start capture")
            return False
        return True
        
    def stopCapture(self):
        if self.__autoGuideThread != None:
            self.__autoGuideThread.stop(True)
            del self.__autoGuideThread
            self.__autoGuideThread = None
        
        if self.__capture != None:
            self.__capture.stopCapture()
            del self.__capture
            self.__capture = None

    def onPreviewInit(self):
        pass
    def onPreviewQuit(self):
        pass
                
    def getFrame(self):
        if self.__autoGuideThread == None or not self.__autoGuideThread.isRunning():
            print("AutoGuideThread Not Running")
            return None
        frm = self.__autoGuideThread.getPreviewFrame()
        if frm == None:
            print("AutoGuideCtrl Frame:None")
            return None
        print("AutoGuideCtrl Frame:OK")
        return frm   
    
    