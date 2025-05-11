import abc
class AbstractLoader:
    __metaclass__=abc.ABCMeta
    @abc.abstractmethod
    def main(self,time_from):
        pass
    @abc.abstractmethod
    def get_recording(self,time_from):
        pass