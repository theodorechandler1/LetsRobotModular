import argparse, configparser #pip install configparser
import time
import logging, logging.handlers
from multiprocessing import Process, Pipe
from ServerCommunicationModule import ServerCommunicationModule #Handles server communication
from robotModuleProcessHandler import robotModuleProcessHandler #Handles loading robot modules

class RobotOrchestrator:
    
    def __init__(self):
        
        #Load configuration
        tempConfig = configparser.ConfigParser()
        tempConfig.read('config.ini')
        
        #Convert the configuration into an easy to use dictionary
        self.config = {}
        for section in tempConfig.sections():
            self.config[section] = {}
            for key, value in tempConfig.items(section):
                self.config[section][key] = value
        
        #Setup Logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.WARNING)
        socketHandler = logging.handlers.SocketHandler(self.config['LogConfig']['log_ip'], logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(socketHandler)
        
        #Check if debugging required
        if(self.config['GlobalConfig']['debug'].lower() == 'true'):
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("In debug mode")
        

        


    
    def orchestrate(self):
        try:
            """
                Main loop which handles passing messages to the robotModuleProcessHandler 
            """
            #Create server processes
            self.serverComm = ServerCommunicationModule(self.config)
            self.serverComm.startServerCommunication()
            
            #Create robot processes
            self.robotModulePlugin = robotModuleProcessHandler(self.config)
            self.robotModulePlugin.createProcesses()
            
            counter = 1
            while True:
                if self.serverComm.chatServerEventPipe.poll() == True:
                    self.robotModulePlugin.sendChatEvent(self.serverComm.chatServerEventPipe.recv())
                if self.serverComm.controlServerEventPipe.poll() == True:
                    self.robotModulePlugin.sendEvent(self.serverComm.controlServerEventPipe.recv())
                for message in self.robotModulePlugin.getMessagesToSend():
                    self.serverComm.chatServerOutboundPipe.send(message)
                counter = counter + 1
        except KeyboardInterrupt:
            #Someone pressed ctrl-c. Shut down everything
            self.logger.info("KeyboardInterrupt. Shutting down all processes")
        except BaseException as e:
            self.logger.critical(e)
        finally:
            self.robotModulePlugin.shutdownProcesses()
            self.serverComm.shutdownServerCommunication()
            logging.shutdown()

if __name__ == '__main__':
    robotOrchestrator = RobotOrchestrator()
    robotOrchestrator.orchestrate()
    