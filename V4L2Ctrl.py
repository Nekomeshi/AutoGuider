
import cv2
import commands
import V4L2Dialog
import shelve


FMT_WIDTH = "WIDTH"
FMT_HEIGHT = "HEIGHT"
FMT_FPS = "FPS"

class CapFormat:
    def __init__(self, index, format):
        self.index = index
        self.formatName = format
        
    format = []

class V4L2Ctl:
    CTRL_BRIGHTNESS =               "brightness"
    CTRL_CONTRAST =                 "contrast"
    CTRL_SATURATION =               "saturation"
    CTRL_WHITE_BALANCE_TEMP_AUTO =  "white_balance_temperature_auto"
    CTRL_GAMMA =                    "gamma"
    CTRL_HUE =                      "hue"
    CTRL_GAIN =                     "gain"
    CTRL_POWER_LINE_FREQ =          "power_line_frequency"
    CTRL_WHITE_BALANCE_TEMP =       "white_balance_temperature"
    CTRL_SHARPNESS =                "sharpness"
    CTRL_EXPOSURE_AUTO =            "exposure_auto"
    CTRL_EXPOSURE_ABSOLUTE =        "exposure_absolute"
    CTRL_FOCUS_ABSOLUTE =           "focus_absolute"
    CTRL_FOCUS_AUTO =               "focus_auto"
    CTRL_BACKLIGHT_COMP =           "backlight_compensation"

    CTRL_LIST = [
        CTRL_BRIGHTNESS,
        CTRL_CONTRAST,
        CTRL_SATURATION,
        CTRL_WHITE_BALANCE_TEMP_AUTO,
        CTRL_GAMMA,
        CTRL_HUE,
        CTRL_GAIN,
        CTRL_POWER_LINE_FREQ,
        CTRL_WHITE_BALANCE_TEMP,
        CTRL_SHARPNESS,
        CTRL_EXPOSURE_AUTO,
        CTRL_EXPOSURE_ABSOLUTE,
        CTRL_FOCUS_ABSOLUTE,
        CTRL_FOCUS_AUTO,
        CTRL_BACKLIGHT_COMP
    ]
        
    TYPE_BOOL = "bool"
    TYPE_INT =  "int"
    TYPE_MENU = "menu"

    __ctrls ={  
        CTRL_BRIGHTNESS:                {"type":"unknown"},
        CTRL_CONTRAST:                  {"type":"unknown"},
        CTRL_SATURATION:                {"type":"unknown"},
        CTRL_WHITE_BALANCE_TEMP_AUTO:   {"type":"unknown"},
        CTRL_GAMMA:                     {"type":"unknown"},
        CTRL_HUE:                       {"type":"unknown"},
        CTRL_GAIN:                      {"type":"unknown"},
        CTRL_POWER_LINE_FREQ:           {"type":"unknown"},
        CTRL_WHITE_BALANCE_TEMP:        {"type":"unknown"},
        CTRL_SHARPNESS:                 {"type":"unknown"},
        CTRL_EXPOSURE_AUTO:             {"type":"unknown"},
        CTRL_EXPOSURE_ABSOLUTE:         {"type":"unknown"},
        CTRL_FOCUS_ABSOLUTE:            {"type":"unknown"},
        CTRL_FOCUS_AUTO:                {"type":"unknown"},
        CTRL_BACKLIGHT_COMP:            {"type":"unknown"}
    }
    __SETTING_FILE_NAME = "V4L2CtrlSetting"
    
    __formatList = {}#list of resolution
    
    __deviceID = 0

    def __getValueFromStrings(self, strs, data):
        for str in strs:
            vals = str.split("=")
            if len(vals) != 2:
                continue
            key = vals[0].strip()
            val = vals[1].strip()
            
            try:
#                print(val)
                data.update({key:int(val)})
            except ValueError:
                print("invalid value({}) = {}".format(key,val))
                pass
            except TypeError:
                pass
                
        return data
    
    def __setInitValue(self):#Not smart (--;
        self.setCtrlValue(self.CTRL_EXPOSURE_AUTO, 1)#Manual Mode
        self.setCtrlValue(self.CTRL_WHITE_BALANCE_TEMP_AUTO, 0)#False
        self.setCtrlValue(self.CTRL_POWER_LINE_FREQ, 0)#Disable
        
        savedImage = shelve.open(self.__SETTING_FILE_NAME)
        for ctrlName in self.CTRL_LIST:  #set all values to center of the range
            ctrl = self.__ctrls.get(ctrlName)
            range = self.getCtrlRange(ctrlName)
            if range == None:
                print("ctrl  " + ctrlName + " does not support Range")
                continue
            #load control value from shelve
            val = None
            if savedImage != None and savedImage.get(ctrlName) != None:
                try:
                    val = int(savedImage[ctrlName])
                    if val < range[0]:
                        val = range[0]
                    elif val > range[1]:
                        val = range[1]
                except ValueError:
                    val = None
            if val == None:
                val = int((range[0] + range[1])/2)
            self.setCtrlValue(ctrlName, val);
        savedImage.close()
        self.setCtrlValue(self.CTRL_BACKLIGHT_COMP, 0)#Disable
        
    
    def __init__(self, device = 0):
        __deviceEnable = False
        self.__deviceID = device
        cmdLine = "v4l2-ctl -d {} --list-ctrls".format(device)
        parmStr = commands.getoutput(cmdLine);
        
        #list available control of connected camera
        for line in parmStr.split(chr(10)):
            line = line.strip()
            v = line.split(":")
            if len(v) != 2:
                print("No split letter : in " + line)
                continue
            ctrlTmp = v[0].split("(")
            if len(ctrlTmp) != 2:
                print("No split letter ( in " + line)
                continue
            ctrlName = ctrlTmp[0].strip()

            dataType = ctrlTmp[1].split(")")[0].strip()

            values = v[1].strip().split(" ")
            for i in range(len(values)):
                values[i] = values[i].strip()
            
            if not self.__ctrls.has_key(ctrlName):
                print("Unknown control : " + ctrlName)
                continue
            prms = self.__ctrls[ctrlName]
            prms["type"] = dataType
            self.__ctrls[ctrlName] = self.__getValueFromStrings(values, prms)
        
#        print("val = {}".format(self.getCtrlValue("white_balance_temperature")))
#        print("range = {}".format(self.getCtrlRange(self.CTRL_GAMMA)))
#        print("setval = {}".format(self.setCtrlValue(self.CTRL_GAMMA, 100)))
#        print(self.__ctrls)
        self.__getFormatsList()
        
        self.__setInitValue()

    def setResolution(self, index, width, height):
        if fmt == None:
            return False
        
        for f in fmt.format:
            if not f.get(self.FMT_WIDTH) == width:
                continue
            if not f.get(self.FMT_HEIGHT) == height:
                continue
            cmdLine = "v4l2-ctl -d {} --set-fmt-video=width={},height={},pixelformat={}".format(self.__deviceID, width, height, index)
            parmStr = commands.getoutput(cmdLine)
            return True
        return False
        
    def __del__(self):
        print("V4L2Ctrl deleted")
        
    #return list of index '0', '1'....
    def getAvailableFormatIndexKeys(self):
        return self.__formatList.keys()
    
    #return list of resolution and fps of specified index
    def getAvailableFormat(self, index):
        fmt = self.__formatList.get(index)
        if fmt == None:
            return None
        return fmt.format
    
    def __getFormatsList(self):
        cmdLine = "v4l2-ctl -d {} --list-formats-ext".format(self.__deviceID)
        parmStr = commands.getoutput(cmdLine)
        
        lines = parmStr.split(chr(10))
        for i in range(len(lines)):
            lines[i] = lines[i].strip()
            
        name = None
        index = -1
        i = 0
        self.__formatList.clear()
        while True:
            while i < len(lines) and not lines[i].startswith("Size: Discrete"):
                line = lines[i]
                if line.startswith("Index"):
                    ll = line.split(":")
                    if len(ll) != 2:
                        i += 1
                        continue
                    index = int(ll[1].strip())
                elif line.startswith("Pixel Format"):
                    ll = line.replace("Pixel Format: ", "")
                    name = ll.strip()
                i+= 1
            if i >= len(lines):
                break

            fmt = self.__formatList.get(str(index))
            if fmt == None:
                fmt = CapFormat(index, name)
                
                self.__formatList[str(index)] = fmt
            
#            print("{} index = {} aa name = {}".format(self.__formatList.keys(), self.__formatList.get(str(index)).index, self.__formatList.get(str(index)).formatName))
            
            line = lines[i]
            s = line.split(" ")
            if len(s) < 1:
                i+=1
                continue
            res = s[len(s)-1].split("x")
            if len(res) != 2:
                i+=1
                continue
            width = int(res[0])
            height = int(res[1])
#            print("{}x{}".format(int(res[0]), int(res[1])))
            i += 1
            while i < len(lines) and not lines[i].startswith("Interval: Discrete"):
                i += 1
            if i >= len(lines):
                break
            line = lines[i]
            s = line.split("(")
            if len(s) < 2:
                i += 1
                continue
            fpss = s[1].split(" ")
            if len(fpss) < 1:
                i += 1
                continue
            fps = float(fpss[0])
#            print("fps {}".format(float(fpss[0])))
            i += 1
            
            if abs(float(width)/float(height) - 1.33) > 0.01: #select aspect 4:3 only
                continue
            
            d = dict({FMT_WIDTH:width, FMT_HEIGHT:height, FMT_FPS:fps})
            fmt.format = fmt.format + [d]

        for index in self.getAvailableFormatIndexKeys():
            fmt = self.__formatList.get(index).format
            fmt.sort(cmp=self.__formatCmp, reverse=True)#sort by resolution size
        print("fmt ={}".format(fmt))

    def __formatCmp(self, a, b):
        aw = a.get(FMT_WIDTH)
        bw = b.get(FMT_WIDTH)
        if aw > bw:
            return 1
        elif aw < bw:
            return -1
        else:
            ah = a.get(FMT_HEIGHT)
            bh = b.get(FMT_HEIGHT)
            if ah > bh:
                return 1
            elif ah < bh:
                return -1
            else:
                af = a.get(FMT_FPS)
                bf = b.get(FMT_FPS)
                if af > bf:
                    return 1
                elif af < bf:
                    return -1
        
        return 0
            
    def __isCtrlAvailable(self, ctrl):
        if not ctrl in self.__ctrls:
            print("No control " + ctrl)
            return False
        values = self.__ctrls[ctrl]
#        print(values["type"])
        
        if values["type"] == "unknown":
            print("Control " + ctrl + " is not supported")
            return False
        
        return True
    
    def getCtrlValue(self, ctrl):
        if not self.__isCtrlAvailable(ctrl):
            return None
        #example of output is white_balance_temperature: 4608
        cmdLine = "v4l2-ctl -d {} --get-ctrl={}".format(self.__deviceID, ctrl)
        parmStr = commands.getoutput(cmdLine)

        val = parmStr.split(":")
        if len(val) != 2:
            print("Invalid response " + parmStr)
            return None
        if val[0].strip() != ctrl:
            print("Invalid command " + val[0])
            return None
        val[1] = val[1].strip()
        try:
            return int(val[1])
        except ValueError, e:
            return None

    def getCtrlRange(self, ctrl):
        if not self.__isCtrlAvailable(ctrl):
            return None    
        values = self.__ctrls[ctrl]
        if values["type"] == self.TYPE_BOOL:
            print("Bool doesn't support range")
            return None
        if not "min" in values or not "max" in values:
            print("Control {} doesn't have range info".format(ctrl))
            return None
        return (values["min"], values["max"])
    
        
        
    def setCtrlValue(self, ctrl, val):
        range = self.getCtrlRange(ctrl)
        if range == None:
            return False
        if range[0] > val or range[1] < val:
            print("val{} is out of range({},{})".format(val, range[0], range[1]))
            return False
        cmdLine = "v4l2-ctl -d {} --set-ctrl={}={}".format(self.__deviceID, ctrl, val)
        print(cmdLine)
        parmStr = commands.getoutput(cmdLine)
        print(parmStr)
        
        #save contrl value to shelve
        savedImage = shelve.open(self.__SETTING_FILE_NAME)
        savedImage[ctrl] = val
        savedImage.close
        
        return True
    
    def getDeviceID(self):
        return self.__deviceID
    
    def isEnable(self):
        return self.__deviceEnable
        
        
    #dialog
    def __onV4L2DlgClose(self, event):
        self.__V4L2Dlg.Close()
    def __onV4L2DlgValueChanged(self, event):
        val = self.__V4L2Dlg.sliderValue.GetValue()        
        self.setCtrlValue(self.__UICtrl, val)
        
    def __onAutoButtonChanged(self, event):
        print("{}".format(self.__V4L2Dlg.auto.GetValue()))
        if self.__V4L2Dlg.auto.GetValue():
            self.setCtrlValue(self.CTRL_EXPOSURE_AUTO, 3)#Auto Mode
        else:
            self.setCtrlValue(self.CTRL_EXPOSURE_AUTO, 1)#Manual Mode
            
    def setCtrlValueUI(self, parent, ctrl):
        rng = self.getCtrlRange(ctrl)
        if rng == None:
            dlg = wx.MessageDialog(parent, 
                                    "Not Supported", 
                                    "Error", 
                                    wx.OK | wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            return None
        
        print("rng = {} : {}".format(rng[0], rng[1]))
        self.__UICtrl = ctrl
        val = self.getCtrlValue(ctrl)
        print("Value = {}".format(val))
        
        sz = parent.GetClientSize()
        y = sz[1] - V4L2Dialog.DIALOG_SIZE [1]-1

        self.__V4L2Dlg = V4L2Dialog.V4L2Dialog(parent, pos = (0, y))
        self.__V4L2Dlg.sliderValue.SetRange(rng[0], rng[1])
        self.__V4L2Dlg.sliderValue.SetValue(val)
        self.__V4L2Dlg.sliderValue.Bind(wx.EVT_SLIDER, self.__onV4L2DlgValueChanged)
        self.__V4L2Dlg.buttonClose.Bind(wx.EVT_BUTTON, self.__onV4L2DlgClose)
        
        if ctrl == self.CTRL_EXPOSURE_ABSOLUTE and self.__isCtrlAvailable(self.CTRL_EXPOSURE_AUTO):
            self.__V4L2Dlg.auto.Enable()
            if self.getCtrlValue(self.CTRL_EXPOSURE_AUTO) == 3:
                self.__V4L2Dlg.auto.SetValue(True)
            else:
                self.__V4L2Dlg.auto.SetValue(False)
                
            self.__V4L2Dlg.auto.Bind(wx.EVT_CHECKBOX, self.__onAutoButtonChanged)
        else:
            self.__V4L2Dlg.auto.Disable()
            
        
        self.__V4L2Dlg.ShowModal()

        val = self.__V4L2Dlg.sliderValue.GetValue()
        print("final val = {}".format(val))
        return val

    
import Capture
import wx
import Preview

    
        
        
class PreviewInterface(Preview.IPreview):
    __width = 0
    __height = 0
    __capture = None
    
    def __init__(self, width, height):
        self.__width = width
        self.__height = height
        
    def onPreviewInit(self):
        self.__capture = Capture.Capture(0, self.__width, self.__height)
        self.__capture.startCapture(15)

    def onPreviewQuit(self):
        self.__capture.stopCapture()
        del self.__capture
        
    def getFrame(self):
        if self.__capture == None:
            return None
        
        return self.__capture.getFrame()        
        
        
        
    

def clickButtonStart(event):
    print("start")
    cap.startPreview(prevInt, 5)
    
def clickButtonStop(event):
    print("Stop")
    cap.stopPreview()
    

def clickButtonClose(event):
    print("Close")
    frame.Close(True)
        
if __name__ == "__main__":
    app = wx.App(False)

    style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.CAPTION)
    frame = wx.Frame(None, wx.ID_ANY, 'HGA Count', size=(320, 240), style = style)
    panel = wx.Panel(frame, wx.ID_ANY)


    buttonStart = wx.Button(panel, wx.ID_ANY, "Start")
    buttonStart.Bind(wx.EVT_BUTTON, clickButtonStart)
    buttonStop = wx.Button(panel, wx.ID_ANY, "Stop")    
    buttonStop.Bind(wx.EVT_BUTTON, clickButtonStop)
    buttonClose = wx.Button(panel, wx.ID_ANY, "Close")    
    buttonClose.Bind(wx.EVT_BUTTON, clickButtonClose)
    cap = Preview.Preview(panel, wx.ID_ANY)

    prevInt = PreviewInterface(320, 240)

    layout = wx.BoxSizer(wx.VERTICAL)
    layout.Add(buttonStart)
    layout.Add(buttonStop)
    layout.Add(buttonClose)
    layout.Add(cap)
    
    v4l2 = V4L2Ctl()
    
    for i in range(2):
        fmt = v4l2.getAvailableFormat().get(str(i))
        print("index = {} xxx name = {}".format(fmt.index, fmt.formatName))

        for ii in fmt.format:
            print("{}".format(ii))
 
    cap = cv2.VideoCapture(0)
    cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
    
    while True:
        ret, frm = cap.read()
        cv2.imshow("AAA", frm)
        cv2.waitKey(1)
        
        
    panel.SetSizer(layout)
    frame.Show()
    frame.ShowFullScreen(True)
    app.MainLoop()
    print("AAAAAA")
    del cap
