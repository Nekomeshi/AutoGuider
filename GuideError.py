
class GuideDirectionInvalidInputError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class GuideDirectionStarLostError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class GuideDirectionStarNotFoundError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class GuideDirectionOutOfFrameError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

