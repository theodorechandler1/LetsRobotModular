from multiprocessing import Process, Pipe
import time
import logging
from robotModule import robotModule
from ChatModule import ChatModule
from PiHatMotorModule import PiHatMotorModule

class robotModuleProcessHandler(object):
    
    def __init__(self, configDict):
        self.config = configDict['robotModuleConfig']
        self.processArray = []
        #Create logger
        self.logIP = configDict['LogConfig']['log_ip']
        self.logger = logging.getLogger(__name__)
        if(self.config['debug'].lower() == 'true'):
            self.logger.setLevel(logging.DEBUG)
            self.debug = True
        else:
            self.debug = False
        #Force debugging
        self.logger.setLevel(logging.DEBUG)
        self.debug = True
        socketHandler = logging.handlers.SocketHandler(self.logIP,logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(socketHandler)
    
    def createProcesses(self):
        self.logger.debug("Creating robot module processes")
        for x in [robotModule(), ChatModule(), PiHatMotorModule()]:
            parentChatEventPipe, childChatEventPipe = Pipe()
            parentChatOutPipe, childChatOutPipe = Pipe()
            parentEventPipe, childEventPipe = Pipe()
            parentShutdownPipe, childShutdownPipe = Pipe()
            r = robotModuleProcess(x, chatEventPipe = childChatEventPipe, chatOutPipe = childChatOutPipe, eventPipe = childEventPipe, shutdownPipe = childShutdownPipe, logIP = self.logIP, debug = self.debug )
            p = Process(target=r.beginProcess, args=())
            self.logger.debug("Starting process: {}".format(p.name))
            p.start()
            self.processArray.append({'process' : p, 'chatPipe' : parentChatEventPipe, 'chatOutPipe' : parentChatOutPipe, 'eventPipe' : parentEventPipe, 'shutdownPipe' : parentShutdownPipe })
    
    def shutdownProcesses(self):
        self.logger.debug("Beginning to shutdown processes")
        for process in self.processArray:
            self.logger.debug("Sending shutdown message to process: {}".format(process['process'].name))
            process['shutdownPipe'].send("Shutdown")
        for process in self.processArray:
            self.logger.debug("Waiting for process {} to finish".format(process['process'].name))
            process['process'].join()
            self.logger.debug("Process {} has finished".format(process['process'].name))
    
    def sendChatEvent(self, args):
        self.logger.debug("Sending chat event to processes")
        for process in self.processArray:
            if process['process'].is_alive():
                process['chatPipe'].send(args)

    def sendEvent(self, args):
        for process in self.processArray:
            if process['process'].is_alive():
                process['eventPipe'].send(args)
    
    def getMessagesToSend(self):
        messages = []
        for process in self.processArray:
            if process['process'].is_alive():
                if process['chatOutPipe'].poll() == True:
                    messages.append(process['chatOutPipe'].recv())
        return messages
    
    
class robotModuleProcess(object):
    '''
        This class is kind of an abstraction layer for multiprocessing. This allows users to make plugins without knowledge of how multiprocessing works
    '''
    def __init__(self, robotModule, chatEventPipe, chatOutPipe, eventPipe, shutdownPipe, logIP, debug):
        self.robotModule = robotModule
        self.chatEventPipe = chatEventPipe
        self.chatOutPipe = chatOutPipe
        self.eventPipe = eventPipe
        self.shutdownPipe = shutdownPipe
        self.logIP = logIP
        self.debug = debug
    
    def _setupLogger(self):
        self.logger = logging.getLogger("ControlServerListener")
        if(self.debug == True):
            self.logger.setLevel(logging.DEBUG)
        socketHandler = logging.handlers.SocketHandler(self.logIP,logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(socketHandler)
    
    
    def beginProcess(self):
        self._setupLogger()
        self.robotModule.passLogger(self.logger)
        self.robotModule.passChatOutputPipe(self.chatOutPipe)
        shutdown = False
        try:
            while(shutdown == False):
                if self.chatEventPipe.poll() == True:
                    #Let the plugin handle the chat event
                    self.robotModule.chatHandler(self.chatEventPipe.recv())
                if self.eventPipe.poll() == True:
                    #Let the plugin handle the movement event
                    self.robotModule.eventHandler(self.eventPipe.recv())
                if self.shutdownPipe.poll() == True:
                    shutdown = True
                #Sleep just a bit so that we don't use all the processing power (I'm sure there is a better way)
                self.robotModule.houseKeeping()
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.logger.debug("Received KeyboardInterrupt")
        except Exception as e:
            self.logger.error("Process {} has encountered an error. Forceably shutting down".format(self.__class__.__name__))
            self.logger.error(e)
            print(e)
            
        finally:
            #Clean up
            #Let the plugin handle the shutdown gracefully
            self.robotModule.shutdown()
            self.chatEventPipe.close()
            self.eventPipe.close()
            self.shutdownPipe.close()
            logging.shutdown()

if __name__ == '__main__':
    #Setup Logging
    FORMAT = '%(asctime)s %(levelname)s, %(module)s: %(message)s'
    logging.basicConfig(format=FORMAT, datefmt='%H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    r = robotModuleProcessHandler(logger)
    r.createProcesses()
    time.sleep(2)
    r.shutdownProcesses()

        
