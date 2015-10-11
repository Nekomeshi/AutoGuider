import wx

class BitmapToggleButton(wx.BitmapButton):
    __onImg = None
    __offImg = None
    __state = False
    
    __callback = None
    
    def __init__(self, parent, ID, onImg, offImg, state = False):
        wx.BitmapButton.__init__(self, parent, ID, onImg)
        self.__onImg = onImg
        self.__offImg = offImg
        self.__state = state
        self.__setBitmap()
        self.Bind(wx.EVT_TOGGLEBUTTON, None)
        pass

    def __setBitmap(self):
        if self.__state:
            self.SetBitmapLabel(self.__onImg)
        else:
            self.SetBitmapLabel(self.__offImg)
            
    def __cb(self, event):
        self.__state = not self.__state
        self.__setBitmap()
        if self.__callback != None:
            self.__callback(event)
            
    def GetValue(self):
        return self.__state
    
    def SetValue(self, val):
        self.__state = val
        self.__setBitmap()
        
    def Bind(self, event, cb):
        if event == wx.EVT_TOGGLEBUTTON:
            self.__callback = cb
            wx.BitmapButton.Bind(self, wx.EVT_BUTTON, self.__cb)
        else:
            wx.BitmapButton.Bind(self, event, cb)
            
                
