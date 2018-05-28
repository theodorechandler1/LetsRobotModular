from socketIO_client import SocketIO, LoggingNamespace
from multiprocessing import Process, Pipe
import urllib2, requests, ssl, traceback, time
import json
import logging, logging.handlers
from datetime import datetime

class ServerCommunicationModule:
    
    def __init__(self, configDict):
        self.config = configDict['ServerConfig']
        #Create logger
        self.logIP = configDict['LogConfig']['log_ip']
        self.logger = logging.getLogger(__name__)
        if(self.config['debug'].lower() == 'true'):
            self.logger.setLevel(logging.DEBUG)
            self.debug = True
        else:
            self.debug = False
        socketHandler = logging.handlers.SocketHandler(self.logIP,logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(socketHandler)
        
        
        self.chatServerEventPipe = None
        self.chatServerInShutdownPipe = None
        self.chatServerInProcess = None
        
        self.chatServerOutPipe = None
        self.chatServerOutShutdownPipe = None
        self.chatServerOutProcess = None
        
        self.controlServerEventPipe = None
        self.controlServerShutdownPipe = None
        self.controlServerProcess = None
        
        self.appServerEventPipe = None
        self.appServerShutdownPipe = None
        self.appServerProcess = None
        
    def startServerCommunication(self):
        #Create Chat Server Inbound Process
        self.logger.debug("Chat Server Inbound process starting")
        parentChatEventPipe, childChatEventPipe = Pipe()
        parentShutdownPipe, childShutdownPipe = Pipe() #logger, chatEventPipe, shutdownPipe, serverURL, robotID
        chatServerInbound = ChatServerInbound(chatEventPipe = childChatEventPipe, shutdownPipe = childShutdownPipe, serverURL = self.config['server_url'], robotID = self.config['robot_id'], debug = self.debug, logIP = self.logIP)
        self.chatServerEventPipe = parentChatEventPipe
        self.chatServerInShutdownPipe = parentShutdownPipe
        self.chatServerInProcess = Process(target=chatServerInbound.chatReceiverStart, args=())
        self.chatServerInProcess.start()
        self.logger.debug("Chat Server Inbound process started")
        
        #Create Chat Server Outbound Process
        self.logger.debug("Chat Server Outbound process starting")
        parentChatOutEventPipe, childChatOutEventPipe = Pipe() 
        parentShutdownPipe, childShutdownPipe = Pipe()
        chatServerOutbound = ChatServerOutbound(childChatOutEventPipe, childShutdownPipe, serverURL = self.config['server_url'], username = self.config['chat_username'], password = self.config['chat_password'], robotID = self.config['robot_id'], chatRoom = self.config['chat_room'], chatSecret = self.config['chat_secret'], debug = self.debug, logIP = self.logIP)
        self.chatServerOutProcess = Process(target=chatServerOutbound.chatSenderStart, args=())
        self.chatServerOutProcess.start()
        self.chatServerOutPipe = parentChatOutEventPipe
        self.chatServerOutShutdownPipe = parentShutdownPipe
        self.logger.debug("Chat Server Outbound process started")
        
        
        #Create Control Server Process
        self.logger.debug("Control Server process starting")
        parentControlEventPipe, childControlEventPipe = Pipe()
        parentShutdownPipe, childShutdownPipe = Pipe()
        controlServer = ControlServerListener(childControlEventPipe, childShutdownPipe, serverURL = self.config['server_url'], robotID = self.config['robot_id'], debug = self.debug, logIP = self.logIP)
        self.controlServerEventPipe = parentControlEventPipe
        self.controlServerShutdownPipe = parentShutdownPipe
        self.controlServerProcess = Process(target=controlServer.controlReceiverStart, args=())
        self.controlServerProcess.start()
        self.logger.debug("Control Server process started")

        
        #Create App Server Process
        self.logger.debug("App Server process starting")
        parentAppEventPipe, childAppEventPipe = Pipe()
        parentShutdownPipe, childShutdownPipe = Pipe()
        appServer = AppServerListener(childAppEventPipe, childShutdownPipe, serverURL = self.config['server_url'], robotID = self.config['robot_id'], controlHostPort = self.config['control_host_port'], debug = self.debug, logIP = self.logIP)
        self.appServerEventPipe = parentAppEventPipe
        self.appServerShutdownPipe = parentShutdownPipe
        self.appServerProcess = Process(target=appServer.appServerStart, args=())
        self.appServerProcess.start()
        self.logger.debug("App Server process started")
        
    def shutdownServerCommunication(self):
        self.logger.debug("Shutting down Server Communication Processes")
        if self.chatServerInShutdownPipe is not None:
            self.chatServerInShutdownPipe.send("Shutdown")
            #If we don't wait we can have a race condition which leads to broken pipes on the logger
            self.logger.debug("Waiting for chatServerInProcess to finish")
            self.chatServerInProcess.join()
            self.logger.debug("chatServerIn process has finished")
        
        if self.chatServerOutShutdownPipe is not None:
            self.chatServerOutShutdownPipe.send("Shutdown")
            #If we don't wait we can have a race condition which leads to broken pipes on the logger
            self.logger.debug("Waiting for chatServerOutProcess to finish")
            self.chatServerOutProcess.join()
            self.logger.debug("chatServerOutProcess has finished")
        
        if self.controlServerShutdownPipe is not None:
            self.controlServerShutdownPipe.send("Shutdown")
            #If we don't wait we can have a race condition which leads to broken pipes on the logger
            self.logger.debug("Waiting for controlServerProcess to finish")
            self.controlServerProcess.join()
            self.logger.debug("controlServerProcess has finished")
        
        if self.appServerShutdownPipe is not None:
            self.appServerShutdownPipe.send("Shutdown")
            #If we don't wait we can have a race condition which leads to broken pipes on the logger
            self.logger.debug("Waiting for appServerProcess to finish")
            self.appServerProcess.join()
            self.logger.debug("appServerProcess has finished")
        
class ControlServerListener(object):
    
    def __init__(self, controlEventPipe, shutdownPipe, serverURL, robotID, debug, logIP):
        self.debug = debug
        self.logIP = logIP
        self.serverURL = serverURL
        self.robotID = robotID
        self.controlEventPipe = controlEventPipe
        self.shutdownPipe = shutdownPipe
        self.controlHostPort = None
        self.commandSocket = None
    
    def _setupLogger(self):
        self.logger = logging.getLogger("ControlServerListener")
        if(self.debug == True):
            self.logger.setLevel(logging.DEBUG)
        socketHandler = logging.handlers.SocketHandler(self.logIP,logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(socketHandler)
    
    def __getControlHostPort(self):
        url = 'https://{}/get_control_host_port/{}'.format(self.serverURL, self.robotID)
        response = ServerHelper.getWithRetry(url)
        self.controlHostPort = json.loads(response)
    
    def controlReceiverStart(self):
        try:
            self._setupLogger()
            self.__getControlHostPort()
            self.logger.debug("Connecting to control socket.io port: {}".format(self.controlHostPort))
            self.commandSocket = SocketIO(self.controlHostPort['host'], self.controlHostPort['port'], LoggingNamespace)
            self.logger.debug("Finished using socket io to connect to control host port: {}".format(self.controlHostPort))
            
            self.commandSocket.on('command_to_robot', self._handleCommand)
            self.commandSocket.on('disconnect', self._handleCommandDisconnect)
            self.commandSocket.on('connect', self._sendRobotID)
            self.commandSocket.on('reconnect', self._sendRobotID)
            
            shutdown = False
            while shutdown == False:
                self.commandSocket.wait(seconds=1)
                if self.shutdownPipe.poll() == True:
                    shutdown = True
                    self.logger.debug("Received shutdown command")
                else:
                    pass
        except KeyboardInterrupt:
            self.logger.debug("KeyboardInterrupt detected")
        except Exception as e:
            raise e
        finally:
            logging.shutdown()
    
    def _handleCommandDisconnect(self):
        self.logger.debug("Command Socket Disconnected")
    
    def _sendRobotID(self):
        self.commandSocket.emit('identify_robot_id', self.robotID)
    
    def _handleCommand(self, *args):
        #Send it upstream to let the orchestrator pass the message out
        self.logger.debug("Received Command: {} from: {}".format(args[0]['command'],args[0]['user']))
        self.controlEventPipe.send(*args)

class ChatServerOutbound(object):

    def __init__(self, chatEventPipe, shutdownPipe, serverURL, username, password, robotID, chatRoom, chatSecret, debug, logIP):
        self.logIP = logIP
        self.debug = debug
        self.serverURL = serverURL
        self.chatPort = 8000
        self.username = username
        self.password = password
        self.robotID = robotID
        self.chatRoom = chatRoom
        self.chatSecret = chatSecret
        self.chatEventPipe = chatEventPipe
        self.shutdownPipe = shutdownPipe
        self.chatSocket = None
        self.chatConnected = False
        self.response = None
    
    def _setupLogger(self):
        self.logger = logging.getLogger("ChatServerOutbound")
        if(self.debug == True):
            self.logger.setLevel(logging.DEBUG)
        socketHandler = logging.handlers.SocketHandler(self.logIP,logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(socketHandler)
    
    def _getCookie(self):
        self.logger.debug("Getting cookie for user: {}".format(self.username))
        headers = {'content-type': 'application/json'}
        url = "https://{}/api/v1/authenticate".format(self.serverURL)
        payload = {'username':self.username, 'password':self.password}
        self.response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
        self.logger.debug(self.response)
    
    def chatSenderStart(self):
        try:
            self._setupLogger()
            if self.username != 'usernameHere':
                self.logger.info("Found username: {} in config file. Attempting to authenicate".format(self.username))
                self._getCookie()
                self.chatSocket = SocketIO('https://{}'.format(self.serverURL), self.chatPort, LoggingNamespace, cookies={'connect.sid' : self.response.cookies['connect.sid']})
            else:
                self.logger.info("Didn't find username in config file. Attempting to connect as annon")
                self.chatSocket = SocketIO('https://{}'.format(self.serverURL), self.chatPort, LoggingNamespace)
            self.chatSocket.on('connect', self._handleConnect)
            self.chatSocket.on('reconnect', self._handleConnect)
            self.chatSocket.on('disconnect', self._handleChatDisconnect)
            lastCommandTime = datetime.now()
            shutdown = False
            #self._sendChatToServer({"message":"[Test] letsrobot.tv","robot_id":self.robotID,"room":self.chatRoom,"secret":self.chatSecret})
            while shutdown == False:
                time.sleep(0.01)
                if self.shutdownPipe.poll() == True:
                    shutdown = True
                    self.logger.debug("Received shutdown command")
                elif self.chatEventPipe.poll() == True and ((datetime.now() - lastCommandTime).seconds > 1): #Check to see if we have something to send and that at least one second has passed since the last message
                    chatToSend = self.chatEventPipe.recv()
                    self.logger.debug("Sending: {} to server".format(chatToSend))
                    self._sendChatToServer({"message":"{}".format(chatToSend),"robot_id":self.robotID,"room":self.chatRoom,"secret":self.chatSecret})
                    lastCommandTime = datetime.now()
                else:
                    pass
        except KeyboardInterrupt:
            self.logger.debug("KeyboardInterrupt detected")
        except BaseException as e:
            print(e)
            raise e
        finally:
            logging.shutdown()
    
    def _handleConnect(self):
        self.logger.debug("Connected")
        pass
    
    def _handleChatDisconnect(self):
        self.logger.debug("Disconnected")
        pass
    
    def _sendChatToServer(self, chatMessage):
        self.logger.debug("Sending chat message")
        self.chatSocket.emit("chat_message",chatMessage)

class ChatServerInbound(object):
    """ 
        This class receives messages from the chat server (generally letsrobot.tv) and passes them to a pipe so that the robot can act on them
    """
    
    def __init__(self, chatEventPipe, shutdownPipe, serverURL, robotID, debug, logIP):
        self.debug = debug
        self.robotID = robotID
        self.serverURL = serverURL
        self.chatEventPipe = chatEventPipe
        self.shutdownPipe = shutdownPipe
        self.chatHostPort = None
        self.chatSocket = None
        self.chatConnected = False
        self.logIP = logIP
        
    def _setupLogger(self):
        self.logger = logging.getLogger("ChatServerInbound")
        if(self.debug == True):
            self.logger.setLevel(logging.DEBUG)
        socketHandler = logging.handlers.SocketHandler(self.logIP,logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(socketHandler)

    def _getChatHostPort(self):
        self.logger.debug("Getting chat host port from server")
        url = 'https://{}/get_chat_host_port/{}'.format(self.serverURL, self.robotID)
        response = ServerHelper.getWithRetry(url)
        self.chatHostPort = json.loads(response)
        self.logger.debug("Found chat host port of: {}".format(self.chatHostPort))
    
    def chatReceiverStart(self):
        try:
            self._setupLogger()
            self._getChatHostPort()
            self.logger.debug("Connecting to chat socket.io port: {}".format(self.chatHostPort))
            self.chatSocket = SocketIO(self.chatHostPort['host'], self.chatHostPort['port'], LoggingNamespace)
            self.logger.debug('Finished using socket io to connect to chat port: {}'.format(self.chatHostPort))
            
            self.chatSocket.on('chat_message_with_name', self._handleChatMessage)
            self.chatSocket.on('connect', self._sendRobotID)
            self.chatSocket.on('reconnect', self._sendRobotID)
            self.chatSocket.on('disconnect', self._handleChatDisconnect)
            
            shutdown = False

            while shutdown == False:
                self.chatSocket.wait(seconds=1)
                if self.shutdownPipe.poll() == True:
                    shutdown = True
                    self.logger.debug("Received shutdown command")
                else:
                    pass
        except KeyboardInterrupt:
            self.logger.debug("KeyboardInterrupt detected")
        except Exception as e:
            raise e
        finally:
            logging.shutdown()
    
    def _sendRobotID(self):
        self.logger.info("Socket connected. Sending robot ID")
        self.chatSocket.emit('identify_robot_id', self.robotID)
        self.chatConnected = True
    
    def _handleChatDisconnect(self):
        self.logger.info("Chat socket disconnected.")
        self.chatConnected = False
    
    def _handleChatMessage(self, *args):
        #Send it upstream to let the orchestrator pass the message out
        try:
            self.logger.debug("Chat Message User: {} sent: {}".format(args[0]['name'],args[0]['message']))
            self.chatEventPipe.send(*args)
        except UnicodeEncodeError:
            self.logger.warning("Chat Message Error. Someone Sent a non ascii message in chat or has a non ascii username")

class AppServerListener(object):
    
    def __init__(self, appEventPipe, shutdownPipe, serverURL, robotID, controlHostPort, debug, logIP):
        self.debug = debug
        self.robotID = robotID
        self.serverURL = serverURL
        self.appEventPipe = appEventPipe
        self.shutdownPipe = shutdownPipe
        self.controlHostPort = controlHostPort
        self.commandSocket = None
        self.logIP = logIP
        self.logHandler = None
    
    def _setupLogger(self):
        self.logger = logging.getLogger("AppServerListener")
        if(self.debug == True):
            self.logger.setLevel(logging.DEBUG)
        self.logHandler = logging.handlers.SocketHandler(self.logIP,logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        self.logger.addHandler(self.logHandler)
    
    def appServerStart(self):
        try:
            self._setupLogger()
            self.logger.debug("Connecting to appserver socket.io port: {}".format(self.controlHostPort))
            self.commandSocket = SocketIO(self.serverURL, self.controlHostPort, LoggingNamespace)
            self.logger.debug("Finished using socket io to connect to appserver host port: {}".format(self.controlHostPort))

            self.commandSocket.on('command_to_robot', self._handleCommand)
            self.commandSocket.on('disconnect', self._handleCommandDisconnect)
            self.commandSocket.on('connect', self._sendRobotID)
            self.commandSocket.on('reconnect', self._sendRobotID)
            shutdown = False
            while (shutdown == False):
                self.commandSocket.wait(seconds=1)
                if self.shutdownPipe.poll() == True:
                    shutdown = True
                    self.logger.debug("Received shutdown command")
                elif self.appEventPipe.poll() == True:
                    pass
                else:
                    pass
        except KeyboardInterrupt:
            self.logger.debug("KeyboardInterrupt detected")
        except BaseException as e:
            print(e)
        finally:
            logging.shutdown()
    
    def _handleCommandDisconnect(self):
        self.logger.debug("Disconnected")
        pass
    
    def _sendRobotID(self):
        self.logger.info("Connected. Sending robot ID")
        self.commandSocket.emit('identify_robot_id', self.robotID)
    
    def _handleCommand(self, *args):
        self.logger.debug("Received command")
        ''' Do nothing with the message. Not currently in use as far as I can tell '''
        pass

class ServerHelper:

    @staticmethod
    def isInternetConnected():
        ''' Checks to see if google is available. Assumes you have internet access if that is the case. '''
        try:
            urllib2.urlopen('https://www.google.com', timeout=1)
            return True
        except urllib2.URLError as err:
            return False 
            
    @staticmethod
    def getWithRetry(url, secure=True):
        for retryNumber in range(2000):
            try:
                if secure:
                    response = urllib2.urlopen(url).read()
                else:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    response = urllib2.urlopen(url, context=ctx).read()
                break
            except:
                #Could not open url
                #traceback.print_exc()
                time.sleep(2)
        return response