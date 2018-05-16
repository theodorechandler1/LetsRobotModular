#This is the class to inherit if you want to extend your robot functionallity 
#DO NOT MODIFY THIS FILE
class robotModule(object):
    def __init__(self):
        #self.chatOutPipe = chatOutPipe
        self.logger = None
        pass
    
    def chatHandler(self, *args):
        #print("chatHandler called")
        pass
    
    def eventHandler(self, *args):
        #print("eventHandler called")
        pass
    
    def sendMessage(self, message):
        self.chatOutPipe.send(message)
        #print("SendMessage called")
        pass
    
    def houseKeeping(self):
        #Called often. Gives the Module a chance to perform various activities without interupting the flow of the program
        pass
    
    def shutdown(self):
        #print("Shutdown called")
        pass
        
    def passLogger(self, logger):
        self.logger = logger