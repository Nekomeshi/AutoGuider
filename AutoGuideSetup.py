import wx
import SetupDialog
import ResolutionSelectDialog
import shelve
import V4L2Ctrl


SEARCH_WINDOW_SIZE_INIT = "SEARCH_WINDOW_INIT"
SEARCH_WINDOW_SIZE_TRACK = "SEARCH_WINDOW_TRACK"
IS_THRES_AUTO = "IS_THRES_AUTO"
THRES_VALUE = "THRES_VALUE"

IS_CALIB_SPEED_HIGH = "IS_CALIB_SPEED_HIGH"
CALIB_LENGTH = "CALIB_LENGTH"

IS_DUTY_AUTO = "IS_DUTY_AUTO"
DUTY_AUTO_MAG = "DUTY_AUTO_MAG"
PWM_CAP_COUNT = "PWM_CAP_COUNT"
PWM_FREQ = "PWM_FREQ"
DUTY_RA = "DUTY_RA"
DUTY_DEC = "DUTY_DEC"


SHOW_PREV_BINARY = "SHOW_PREV_BINARY"
CURRENT_RESOLUTION = "CURRENT_RESOLUTION"
RESIZE_RESOLUTION = "RESIZE_RESOLUTION"
RETURN_TO_ORG_POS_ON_CALIB_RA = "RETURN_TO_ORG_POS_ON_CALIB_RA"
RETURN_TO_ORG_POS_ON_CALIB_DEC = "RETURN_TO_ORG_POS_ON_CALIB_DEC"


AUTO_GUIDE_SETTING_NAME= "AutoGuideSettings"

class AutoGuideSetup:
    __setupDialog = None
    __resChangeDialog = None
    __availableFormat = None
    __parentWindow = None
    
    __isOKClicked = False
    
    
    def __init__(self, v4l2):
        
        fmtIndex = v4l2.getAvailableFormatIndexKeys()
        if len(fmtIndex) == 0:
            return
        self.__availableFormat = v4l2.getAvailableFormat(fmtIndex[0])
        
    def __saveSetupValue(self):
        needToReboot = False
        dlg = self.__setupDialog
        if dlg == None:
            return needToReboot
        
        global searchWindowSizeInit
        global searchWindowSizeTrack
        global isThresAuto
        global thresValue
        
        global isCalibSpeedHigh
        global calibLength

        global isDutyAuto
        global dutyAutoMag
        global pwmCapCount
        global pwmFreq
        global dutyRa
        global dutyDec

        global isShowPreviewBinary
        global currentResolution
        global resizeResolution
        global ret2OrgPosRa
        global ret2OrgPosDec
        
        
        searchWindowSizeInit = dlg.spinInitWindowSize.GetValue()
        searchWindowSizeTrack = dlg.spinTrackWindowSize.GetValue()
        isThresAuto = dlg.checkThresAuto.GetValue()
        thresValue = dlg.spinThresValue.GetValue()
        
        isCalibSpeedHigh = dlg.checkIsCalibSpeedHigh.GetValue()
        calibLength = dlg.spinCalibLength.GetValue()
        

        isDutyAuto = dlg.checkboxDutyAuto.GetValue()
        dutyAutoMag = dlg.sliderAutoMag.GetValue()
        pwmCapCount = dlg.spinPWMCapCount.GetValue()
        freq  = dlg.sliderPWMFreq.GetValue()
        if freq != pwmFreq:
            pwmFreq = freq
            needToReboot = True


        dutyRa = dlg.sliderDutyRa.GetValue()
        dutyDec = dlg.sliderDutyDec.GetValue()
        
        isShowPreviewBinary = dlg.showPreviewBinary.GetValue()
        res = self.__convText2Res(dlg.textResolution.GetValue())
        if res != currentResolution:
            currentResolution = res
            needToReboot = True
            
        resizeResolution = dlg.checkResize.GetValue()
        ret2OrgPosRa = dlg.checkReturnRa.GetValue()
        ret2OrgPosDec = dlg.checkReturnDec.GetValue()
        
        
        
        savedData = shelve.open(AUTO_GUIDE_SETTING_NAME)
        savedData[SEARCH_WINDOW_SIZE_INIT] = searchWindowSizeInit
        savedData[SEARCH_WINDOW_SIZE_TRACK] = searchWindowSizeTrack
        savedData[IS_THRES_AUTO] = isThresAuto
        savedData[THRES_VALUE] = thresValue
        
        savedData[IS_CALIB_SPEED_HIGH] = isCalibSpeedHigh
        savedData[CALIB_LENGTH] = calibLength
        
        savedData[IS_DUTY_AUTO] = isDutyAuto
        savedData[DUTY_AUTO_MAG] = dutyAutoMag
        savedData[PWM_CAP_COUNT] = pwmCapCount
        savedData[PWM_FREQ] = pwmFreq
        savedData[DUTY_RA] = dutyRa
        savedData[DUTY_DEC] = dutyDec

        savedData[SHOW_PREV_BINARY] = isShowPreviewBinary
        savedData[CURRENT_RESOLUTION] = currentResolution
        savedData[RESIZE_RESOLUTION] = resizeResolution

        savedData[RETURN_TO_ORG_POS_ON_CALIB_RA] = ret2OrgPosRa
        savedData[RETURN_TO_ORG_POS_ON_CALIB_DEC] = ret2OrgPosDec
        
        savedData.close()
        
        return needToReboot

    #Open setup dialog                
    def showDialog(self, parent):
        
        global currentResolution
        
        self.__parentWindow = parent

        self.__setupDialog = SetupDialog.SetupDialog(parent)
        dlg = self.__setupDialog

        #set values to UI parts
        dlg.buttonOK.Bind(wx.EVT_BUTTON, self.__onClickedOK)
        dlg.buttonCancel.Bind(wx.EVT_BUTTON, self.__onClickedCancel)
        dlg.checkThresAuto.Bind(wx.EVT_CHECKBOX, self.__onThresCheckBoxChanged)
        dlg.buttonChangeResolution.Bind(wx.EVT_BUTTON, self.__onClickResChange)

        dlg.checkboxDutyAuto.Bind(wx.EVT_CHECKBOX, self.__onIsDutyAutoCheckBoxChanged)
        dlg.checkboxDutyAuto.SetValue(isDutyAuto)
        
        
        dlg.checkIsCalibSpeedHigh.SetValue(isCalibSpeedHigh)
        dlg.spinCalibLength.SetValue(calibLength)
        
        dlg.sliderAutoMag.SetValue(dutyAutoMag)
        dlg.spinPWMCapCount.SetValue(pwmCapCount)
        dlg.sliderPWMFreq.SetValue(pwmFreq)
        
        dlg.sliderDutyRa.SetValue(dutyRa)
        dlg.sliderDutyDec.SetValue(dutyDec)

        self.__setupPWMUIVisibility(isDutyAuto)
        

        dlg.spinInitWindowSize.SetValue(searchWindowSizeInit)
        dlg.spinTrackWindowSize.SetValue(searchWindowSizeTrack)
        dlg.checkThresAuto.SetValue(isThresAuto)
        dlg.spinThresValue.SetValue(thresValue)
        dlg.checkResize.SetValue(resizeResolution)
        
        dlg.checkReturnRa.SetValue(ret2OrgPosRa)
        dlg.checkReturnDec.SetValue(ret2OrgPosDec)
        
        
        if currentResolution == None:
            f = self.__availableFormat[0]
            currentResolution = (f.get("WIDTH"), f.get("HEIGHT"))
            
        dlg.textResolution.SetValue(self.__convRes2Text(currentResolution))
        
        if isThresAuto:
            dlg.spinThresValue.Disable()
        else:
            dlg.spinThresValue.Enable()
        
        
            
        dlg.showPreviewBinary.SetValue(isShowPreviewBinary)
        
        self.__isOKClicked = False
        self.__setupDialog.ShowModal()
        if self.__isOKClicked:
            return wx.ID_OK
        else:
            return wx.ID_CANCEL

    def __setupPWMUIVisibility(self, isDutyAuto):
        dlg = self.__setupDialog
        if isDutyAuto:
            dlg.sliderDutyRa.Disable()
            dlg.sliderDutyDec.Disable()
            dlg.sliderAutoMag.Enable()
            dlg.spinPWMCapCount.Enable()
        else:
            dlg.sliderDutyRa.Enable()
            dlg.sliderDutyDec.Enable()
            dlg.sliderAutoMag.Disable()
            dlg.spinPWMCapCount.Disable()
        
    def __onIsDutyAutoCheckBoxChanged(self, event):
        dlg = self.__setupDialog
        self.__setupPWMUIVisibility(dlg.checkboxDutyAuto.GetValue())
        
    def __onThresCheckBoxChanged(self, event):
        dlg = self.__setupDialog
        if dlg.checkThresAuto.GetValue():
            dlg.spinThresValue.Disable()
        else:
            dlg.spinThresValue.Enable()
        
    def __onClickedOK(self, event):
        if self.__setupDialog == None:
            return
        
        self.__isOKClicked = True
        
        needToReboot = self.__saveSetupValue()
        self.__setupDialog.Close()
        self.__setupDialog = None
        if needToReboot:
            dlg = wx.MessageDialog(self.__parentWindow, 
                                    "Need to restart app\n to enable some values.", 
                                    "Caution", 
                                    wx.OK | wx.ICON_EXCLAMATION).ShowModal()
        self.__parentWindow = None

    def __onClickedCancel(self, event):
        if self.__setupDialog == None:
            return
        self.__setupDialog.Close()
        self.__setupDialog = None
        self.__parentWindow = None

    #convert resolution <-> text in resolution list
    def __convRes2Text(self, res):
        return "{} x {}".format(res[0], res[1])
    
    def __convText2Res(self, str):
        try:
            sp = str.split("x")
            return (int(sp[0].strip()), int(sp[1].strip()))
        except:
            print("invalid resolution info {}".format(str))
            return None
        
    #resolution list dialog
    def __onClickResChangeOK(self, event):
        result = self.__resChangeDialog.listBoxResolution.GetStringSelection()
        resolution = None
        if result != None:
            resolution = self.__convText2Res(result)
            self.__setupDialog.textResolution.SetValue(result)
        else:
            print("No resolution selected")
            
        self.__resChangeDialog.Close()
        self.__resChangeDialog = None
        
    def __onClickResChangeCancel(self, event):
        self.__resChangeDialog.Close()
        self.__resChangeDialog = None
        
    def __onClickResChange(self, event):
        if self.__setupDialog == None:
            print("Setup dialog is not open")
            return
        dlg = ResolutionSelectDialog.ResolutionSelectDialog(self.__setupDialog)
        dlg.bitmapButtonOK.Bind(wx.EVT_BUTTON, self.__onClickResChangeOK)
        dlg.bitmapButtonCancel.Bind(wx.EVT_BUTTON, self.__onClickResChangeCancel)
        list = []
        selString = ""
        for f in self.__availableFormat:
            w = f.get("WIDTH")
            h = f.get("HEIGHT")
            
            txt = self.__convRes2Text((w, h))
            list.append(txt)
            if txt == self.__setupDialog.textResolution.GetValue():
                selString = txt
        
        dlg.listBoxResolution.Set(list)
        dlg.listBoxResolution.SetStringSelection(selString, True)
        del list
        
        self.__resChangeDialog = dlg
        self.__resChangeDialog.ShowModal()



    @staticmethod
    def getWindowSizeInit(shlv):
        try:
            return int(shlv[SEARCH_WINDOW_SIZE_INIT])
        except:
            return 20
    
    @staticmethod
    def getWindowSizeTrack(shlv):
        try:
            return int(shlv[SEARCH_WINDOW_SIZE_TRACK])
        except:
            return 10
    @staticmethod
    def isThresAuto(shlv):
        try:
            return shlv[IS_THRES_AUTO]
        except:
            return True
    
    @staticmethod
    def getThresValue(shlv):
        try:
            return shlv[THRES_VALUE]
        except:
            return 128
        
    @staticmethod
    def getIsCalibSpeedHigh(shlv):
        try:
            return shlv[IS_CALIB_SPEED_HIGH]
        except:
            return False
        
    @staticmethod
    def getCalibLength(shlv):
        try:
            return shlv[CALIB_LENGTH]
        except:
            return 10
        
    @staticmethod
    def isDutyAuto(shlv):
        try:
            return shlv[IS_DUTY_AUTO]
        except:
            return True
    @staticmethod
    def dutyAutoMag(shlv):
        try:
            return shlv[DUTY_AUTO_MAG]
        except:
            return 1
        
    @staticmethod
    def pwmCapCount(shlv):
        try:
            return shlv[PWM_CAP_COUNT]
        except:
            return 5
        
        
    @staticmethod
    def pwmFreq(shlv):
        try:
            return shlv[PWM_FREQ]
        except:
            return 20
        
    @staticmethod
    def getDutyRa(shlv):
        try:
            return shlv[DUTY_RA]
        except:
            return 50
        
    @staticmethod
    def getDutyDec(shlv):
        try:
            return shlv[DUTY_DEC]
        except:
            return 50
        
    @staticmethod
    def isShowPrevBinary(shlv):
        try:
            return shlv[SHOW_PREV_BINARY]
        except:
            return False
    @staticmethod
    def getCurrentResolution(shlv):
        try:
            return shlv[CURRENT_RESOLUTION]
        except:
            return None
    @staticmethod
    def getResizeResolution(shlv):
        try:
            return shlv[RESIZE_RESOLUTION]
        except Exception, e:
            return True    
    @staticmethod
    def getRet2OrgPosRA(shlv):
        try:
            return shlv[RETURN_TO_ORG_POS_ON_CALIB_RA]
        except Exception, e:
            return True
    @staticmethod
    def getRet2OrgPosDEC(shlv):
        try:
            return shlv[RETURN_TO_ORG_POS_ON_CALIB_DEC]
        except Exception, e:
            return True
        
#load setting info        
savedData = shelve.open(AUTO_GUIDE_SETTING_NAME)
searchWindowSizeInit = AutoGuideSetup.getWindowSizeInit(savedData)
searchWindowSizeTrack = AutoGuideSetup.getWindowSizeTrack(savedData)
isThresAuto = AutoGuideSetup.isThresAuto(savedData)
thresValue = AutoGuideSetup.getThresValue(savedData)


isCalibSpeedHigh = AutoGuideSetup.getIsCalibSpeedHigh(savedData)
calibLength = AutoGuideSetup.getCalibLength(savedData)

isDutyAuto = AutoGuideSetup.isDutyAuto(savedData)
dutyAutoMag = AutoGuideSetup.dutyAutoMag(savedData)

pwmCapCount = AutoGuideSetup.pwmCapCount(savedData);
pwmFreq = AutoGuideSetup.pwmFreq(savedData)

dutyRa = AutoGuideSetup.getDutyRa(savedData)
dutyDec = AutoGuideSetup.getDutyDec(savedData)


isShowPreviewBinary = AutoGuideSetup.isShowPrevBinary(savedData)
currentResolution = AutoGuideSetup.getCurrentResolution(savedData)
resizeResolution = AutoGuideSetup.getResizeResolution(savedData)
ret2OrgPosRa = AutoGuideSetup.getRet2OrgPosRA(savedData)
ret2OrgPosDec = AutoGuideSetup.getRet2OrgPosDEC(savedData)

savedData.close()
