import wx
import cv2
import threading
import time

class CaptureThread(threading.Thread):
    __sleepTime = 1
    __isRunning = False
    __camera = None
    __frame = None
    __lockFrame = None
    __width = -1
    __height = -1

    def __init__(self, camera, width = -1, height = -1, fps = 15.0):
        super(CaptureThread, self).__init__()
        self.__sleepTime  = 1.0/float(fps)
        self.__camera = camera
        print("camera = {}".format(self.__camera))
        self.__lockFrame = threading.Lock()
        self.__height = height
        self.__width = width
        
    def run(self):
        self.__isRunning = True
        while self.__isRunning:
            tm1 = time.time()
            #using the convination of two method, result is same
            #self.__camera.grab()
            #self.__camera.retrieve()
            ret, frame = self.__camera.read()
            self.__lockFrame.acquire()
            if ret and frame != None:
                if self.__width > 0:
                    self.__frame = cv2.resize(frame, (self.__width, self.__height))
                    self.__frame = cv2.cvtColor(self.__frame, cv2.COLOR_BGR2RGB)
                else:
                    self.__frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                self.__frame = None
            self.__lockFrame.release()
            tm2 = time.time()
    
            st = max(self.__sleepTime - (tm2 - tm1), 0.01)

            print("RAP = {}mS wait = {}mS".format((tm2-tm1)*1000, st*1000) )

            time.sleep(st)
    
    def stop(self, waitEndThread = False):
        self.__isRunning = False
        if waitEndThread:
            self.join()
            
    def getFrame(self):
        self.__lockFrame.acquire()
        frame = self.__frame
        self.__lockFrame.release()
        return frame
        
        
        
class Capture:
    __camera = None
    __width = 0
    __height = 0
    __capThread = None
    __captureOnAnotherThread = False

    def __init__(self, id, width, height, maxWidth = -1, maxHeight = -1, captureOnAnotherThread = False):
        self.__camera = cv2.VideoCapture(id)
        if not self.__camera.isOpened():
            self.__camera = None
            return
        self.__width = width
        self.__height = height
        
        self.__camera.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, maxWidth)
        self.__camera.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, maxHeight)
        self.__camera.set(cv2.cv.CV_CAP_PROP_FPS, 5)
        self.__captureOnAnotherThread = captureOnAnotherThread

    def __del__(self):
        print("Deleting Capture object")
        if self.__camera == None:
            return
        if self.__captureOnAnotherThread:
            if self.__isCaptureStarted():
                self.stopCapture()
            
        self.__camera.release()
        self.__camera = None
        
    def isCameraAvailable(self):
        return self.__camera != None
    
    def __isCaptureStarted(self):
        if not self.isCameraAvailable():
            return False
        
        if not self.__captureOnAnotherThread:
            return True
        
        if self.__capThread == None:
            return False
        if not self.__capThread.isAlive():
            return False
        
        return True
        
    def startCapture(self, fps = 30):
        if not self.isCameraAvailable():
            print("Can not start capture because camera is not available")
            return False
        
        self.__camera.set(cv2.cv.CV_CAP_PROP_FPS, fps)
        if not self.__captureOnAnotherThread:
            return True
    
        self.__capThread = CaptureThread(self.__camera, self.__width, self.__height, fps)
        self.__capThread.start()
        return True
    
    def stopCapture(self):
        print("Stop")
        if not self.__captureOnAnotherThread:
            return
        
        if not self.__isCaptureStarted():
            return
        self.__capThread.stop()
        print("waiting thread stop")
        self.__capThread.join()
        print("thread stopped")
        
        self.__capThread = None
        
    def getFrame(self):
        if not self.isCameraAvailable():
            print("Camera not available")
            return None
        if not self.__captureOnAnotherThread:
            ret, frame = self.__camera.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame = None
            return frame    
        
        
        if not self.__isCaptureStarted():
            print("not started")
            return None
        frame = self.__capThread.getFrame()#if frame is invalid, None is returned
        return frame