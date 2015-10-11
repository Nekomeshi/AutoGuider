import wx
import time
import Capture
import abc

class IPreview():
    def __init__(self):
        pass
    def __del__(self):
        pass
        
    @abc.abstractmethod
    def onPreviewInit(self):
        pass
    @abc.abstractmethod
    def onPreviewQuit(self):
        pass
    @abc.abstractmethod
    def getFrame(self):
        pass
        

class Preview(wx.Panel):
    __bmp = None
    __img = None
    __timer = None
    __iPreview = None
    __dcWidth = None
    __dcHeight = None
    
    def __init__(self, parent, id):
        wx.Panel.__init__(self, parent, id)
        
    def __del__(self):
        self.stopPreview()
        del self.__capture
        
    def startPreview(self, iPreview, fps=5):
        self.__iPreview = iPreview
        dc = wx.BufferedPaintDC(self)
        self.__dcWidth, self.__dcHeight = dc.GetSize()
        del dc
        
        self.__bmp = wx.EmptyBitmap(self.__dcWidth, self.__dcHeight, 24)
        self.__img = wx.EmptyImage(self.__dcWidth, self.__dcHeight)

        self.Bind(wx.EVT_PAINT, self.__onPaint)
        self.Bind(wx.EVT_TIMER, self.__nextFrame)

        iPreview.onPreviewInit()
        
        self.__timer = wx.Timer(self)
        self.__timer.Start(1000./fps)


    def stopPreview(self):
        self.__iPreview.onPreviewQuit()

        if not self.__timer:
            self.__timer.cancel()
            self.__timer = None
            
        
        
    def __onPaint(self, evt):
        if not self.__bmp:
            return
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.__bmp, 0, 0)
        del dc

    def __nextFrame(self, event):

        frame = self.__iPreview.getFrame()
        if frame != None:
            #crop frame to fit to DC
            h, w = frame.shape[:2]
            minW = min(w, self.__dcWidth)
            minH = min(h, self.__dcHeight)
#            print("{}x{}".format(minW, minH))
            top = (h - minH)/2
            lft = (w - minW)/2
            self.__img.SetData(frame[top:top+minH, lft:lft+minW].tostring())
            self.__bmp = self.__img.ConvertToBitmap()
            self.Refresh()

