import RPi.GPIO as GPIO
import GuideCtrlDialog

import wx

class GuideCtrl:
    __PWM_FREQ = 20 #Hz
    
    __GPIO_SPEED_SELECT = 16
    __GPIO_DU = 20
    __GPIO_DD = 21
    __GPIO_RR = 13
    __GPIO_RL = 19
    __GPIO_INPUT_SELECT = 26

    __pwmInfo = {}
    __isHighSpeed = False
    __onInputChanged = None

        
    def __init__(self, pwmFreq, onInputChanged = None):
        self.__PWM_FREQ = pwmFreq
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.__GPIO_DU, GPIO.OUT)
        pwmDU = GPIO.PWM(self.__GPIO_DU, self.__PWM_FREQ)
        pwmDU.start(0)
        self.__setPWMInfo(self.__GPIO_DU, pwmDU, 0)
                
        GPIO.setup(self.__GPIO_DD, GPIO.OUT)
        pwmDD = GPIO.PWM(self.__GPIO_DD, self.__PWM_FREQ)
        pwmDD.start(0)
        self.__setPWMInfo(self.__GPIO_DD, pwmDD, 0)
        
        GPIO.setup(self.__GPIO_RR, GPIO.OUT)
        pwmRR = GPIO.PWM(self.__GPIO_RR, self.__PWM_FREQ)
        pwmRR.start(0)
        self.__setPWMInfo(self.__GPIO_RR, pwmRR, 0)

        GPIO.setup(self.__GPIO_RL, GPIO.OUT)
        pwmRL = GPIO.PWM(self.__GPIO_RL, self.__PWM_FREQ)
        pwmRL.start(0)
        self.__setPWMInfo(self.__GPIO_RL, pwmRL, 0)
        
        GPIO.setup(self.__GPIO_SPEED_SELECT, GPIO.OUT)
        self.ctrlSpeed(False)

        GPIO.setup(self.__GPIO_INPUT_SELECT, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        self.__onInputChanged = onInputChanged
        if self.__onInputChanged != None:
            GPIO.add_event_detect(self.__GPIO_INPUT_SELECT, 
                                GPIO.BOTH, callback = self.__onInputChanged, 
                                bouncetime=400)
        

    def __del__(self):
        for key in self.__pwmInfo:
            pwm, duty = self.__pwmInfo[key]
            print key, pwm, duty
            pwm.stop()
            GPIO.setup(key, GPIO.IN)

        if self.__onInputChanged != None:
            GPIO.remove_event_detect(self.__GPIO_SPEED_SELECT)
            
        print("GuideCtrl deleted")

    def __setPWMInfo(self, port, pwm, duty):
        self.__pwmInfo[port] = [pwm, duty]
        
    def __ctrlGPIO(self, port, setOn):
        if setOn:
            GPIO.output(port, GPIO.HIGH)
        else:
            GPIO.output(port, GPIO.LOW)

    def __ctrlPWM(self, port, duty):#duty should be between 0 to 100
        if duty < 0:
            duty = 0
        elif duty > 100:
            duty = 100
        pwm, tmp = self.__pwmInfo[port]
        pwm.ChangeDutyCycle(duty)
        self.__setPWMInfo(port, pwm, duty)
            
    def ctrlDU(self, duty):
        self.__ctrlPWM(self.__GPIO_DU, duty)
    def isDUOn(self):
        pwm, duty = self.__pwmInfo[self.__GPIO_DU]
        return duty > 0
        
    def ctrlDD(self, duty):
        self.__ctrlPWM(self.__GPIO_DD, duty)
    def isDDOn(self):
        pwm, duty = self.__pwmInfo[self.__GPIO_DD]
        return duty > 0

    def ctrlRR(self, duty):
        self.__ctrlPWM(self.__GPIO_RR, duty)
    def isRROn(self):
        pwm, duty = self.__pwmInfo[self.__GPIO_RR]
        return duty > 0
        
    def ctrlRL(self, duty):
        self.__ctrlPWM(self.__GPIO_RL, duty)
    def isRLOn(self):
        pwm, duty = self.__pwmInfo[self.__GPIO_RL]
        return duty > 0

    def ctrlSpeed(self, setHighSpeed):
        self.__isHighSpeed = setHighSpeed
        self.__ctrlGPIO(self.__GPIO_SPEED_SELECT, setHighSpeed)
    def isHighSpeed(self):
        return self.__isHighSpeed

    def isInputRPi(self):
        return GPIO.input(self.__GPIO_INPUT_SELECT) == GPIO.HIGH


    def stopAll(self):
        self.stopRa()
        self.stopDec()
    def stopRa(self):
        self.ctrlRR(0)
        self.ctrlRL(0)
    def stopDec(self):
        self.ctrlDD(0)
        self.ctrlDU(0)
    def toRaPlus(self, duty):
        self.ctrlRR(duty)
        self.ctrlRL(0)
    def toRaMinus(self, duty):
        self.ctrlRR(0)
        self.ctrlRL(duty)
    def toDecPlus(self, duty):
        self.ctrlDU(duty)
        self.ctrlDD(0)
    def toDecMinus(self, duty):
        self.ctrlDU(0)
        self.ctrlDD(duty)




    #guide controller
    def __onGuideControllerClose(self, event):
        self.__GuideDlg.Close()

    def __setDirButttonAppearance(self, button, state):
        if state:
            button.SetBackgroundColour("#804040")
        else:
            button.SetBackgroundColour("#404040")
            
    def __onToggleClick(self, event):
        btn = None
        ctrl = None
        id = event.GetId()
        if id == GuideCtrlDialog.BUTTON_LEFT:
            btn = self.__GuideDlg.buttonLeft
            ctrl = self.ctrlRL
            print("LEFT")
        elif id == GuideCtrlDialog.BUTTON_RIGHT:
            btn = self.__GuideDlg.buttonRight
            ctrl = self.ctrlRR
            print("RIGHT")
        elif id == GuideCtrlDialog.BUTTON_UP:
            btn = self.__GuideDlg.buttonUp
            ctrl = self.ctrlDU
            print("UP")
        elif id == GuideCtrlDialog.BUTTON_DOWN:
            btn = self.__GuideDlg.buttonDown
            ctrl = self.ctrlDD
            print("DOWN")
        state = btn.GetValue()
        self.__setDirButttonAppearance(btn, state)
        if state:
            ctrl(100)
        else:
            ctrl(0)
            
    def __setSpeedButtonAppearance(self, state):
        if state:
            self.__GuideDlg.buttonSpeed.SetLabel("Hi")
            self.__GuideDlg.buttonSpeed.SetBackgroundColour("#804040")
        else:
            self.__GuideDlg.buttonSpeed.SetLabel("Lo")
            self.__GuideDlg.buttonSpeed.SetBackgroundColour("#408040")
    
    def __onToggleSpeedClick(self, event):
        btn = self.__GuideDlg.buttonSpeed
        state = btn.GetValue()
        self.__setSpeedButtonAppearance(state)
        self.ctrlSpeed(state)
        
    def __guideControllerBind(self):
        self.__GuideDlg.buttonClose.Bind(wx.EVT_BUTTON, self.__onGuideControllerClose)
        self.__GuideDlg.buttonLeft.Bind(wx.EVT_TOGGLEBUTTON, self.__onToggleClick)
        self.__GuideDlg.buttonRight.Bind(wx.EVT_TOGGLEBUTTON, self.__onToggleClick)
        self.__GuideDlg.buttonUp.Bind(wx.EVT_TOGGLEBUTTON, self.__onToggleClick)
        self.__GuideDlg.buttonDown.Bind(wx.EVT_TOGGLEBUTTON, self.__onToggleClick)
        self.__GuideDlg.buttonSpeed.Bind(wx.EVT_TOGGLEBUTTON, self.__onToggleSpeedClick)
                    
    def __setInitState(self):
        state = self.isDUOn()
        self.__GuideDlg.buttonUp.SetValue(state)
        self.__setDirButttonAppearance(self.__GuideDlg.buttonUp, state)
        state = self.isDDOn()
        self.__GuideDlg.buttonDown.SetValue(state)
        self.__setDirButttonAppearance(self.__GuideDlg.buttonDown, state)
        state = self.isRROn()
        self.__GuideDlg.buttonRight.SetValue(state)
        self.__setDirButttonAppearance(self.__GuideDlg.buttonRight, state)
        state = self.isRLOn()
        self.__GuideDlg.buttonLeft.SetValue(state)
        self.__setDirButttonAppearance(self.__GuideDlg.buttonLeft, state)
        
        state = self.isHighSpeed()
        self.__GuideDlg.buttonSpeed.SetValue(state)
        self.__setSpeedButtonAppearance(state)

            
    def showGuideController(self, parent):
        sz = parent.GetClientSize()
        y = sz[1] - GuideCtrlDialog.DIALOG_SIZE [1]-1
        self.__GuideDlg = GuideCtrlDialog.GuideCtrlDialog(parent, pos = (0, y))
        self.__setInitState()
        self.__guideControllerBind()
        self.__GuideDlg.ShowModal()

3