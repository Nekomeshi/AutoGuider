
import RPi.GPIO as GPIO
import commands

class PiTFT28Ctrl:
    
    __isBacklightOn = True
    __isGPIOCallBackSet = {18:False, 
                           22:False,
                           23:False,
                           27:False}

            
    def __init__(self):
        cmdLine = 'sudo sh -c "echo 508 > /sys/class/gpio/export"'        
        commands.getoutput(cmdLine);
        cmdLine = "sudo sh -c \"echo \'out\' > /sys/class/gpio/gpio508/direction\" "
        commands.getoutput(cmdLine);
        self.backlight(isOn = True)
        self.__isBacklightOn = True

        GPIO.setmode(GPIO.BCM)

    def __del__(self):
        self.backlight(isOn = True)
        cmdLine = "sudo sh -c \"echo \'in\' > /sys/class/gpio/gpio508/direction\" "
        commands.getoutput(cmdLine);
        self.setGPIO18Callback(callback = None)
        self.setGPIO22Callback(callback = None)
        self.setGPIO23Callback(callback = None)
        self.setGPIO27Callback(callback = None)
        print("PiTFT28Ctrl deleted")
            
    #backlight setting
    def backlight(self, isOn):
        if isOn:
            value = 1
        else:
            value = 0
        cmdLine = "sudo sh -c \"echo \'{}\' > /sys/class/gpio/gpio508/value\"".format(value)
        commands.getoutput(cmdLine);
        self.__isBacklightOn = isOn
    
    def isBacklightOn(self):
        return self.__isBacklightOn

    def callback(self, event):
        print("AAAA")
        
    #SW setting
    def __setGPIOCallback(self, port, cb, init_state, trigger):
        if cb == None:
            if not self.__isGPIOCallBackSet[port]:
                return
            self.__isGPIOCallBackSet[port] = False
            GPIO.remove_event_detect(port)
            return
        
        GPIO.setup(port, GPIO.IN, pull_up_down = init_state)
        print("Cb = {}".format(cb))
        GPIO.add_event_detect(port, trigger, callback= cb, bouncetime = 200)
        self.__isGPIOCallBackSet[port] = True
        

    def setGPIO18Callback(self, 
                        callback, 
                        init_state = GPIO.PUD_DOWN, 
                        trigger = GPIO.RISING):
        self.__setGPIOCallback(18, callback, init_state, trigger)
    
    def setGPIO22Callback(self, 
                        callback, 
                        init_state = GPIO.PUD_DOWN, 
                        trigger = GPIO.RISING):
        self.__setGPIOCallback(22, callback, init_state, trigger)
        
    def setGPIO23Callback(self, 
                        callback, 
                        init_state = GPIO.PUD_DOWN, 
                        trigger = GPIO.RISING):
        self.__setGPIOCallback(23, callback, init_state, trigger)

    def setGPIO27Callback(self, 
                        callback, 
                        init_state = GPIO.PUD_DOWN, 
                        trigger = GPIO.RISING):
        self.__setGPIOCallback(27, callback, init_state, trigger)
