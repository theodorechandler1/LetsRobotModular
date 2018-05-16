print("DemoModule Imported")

class demoModule(object):
    def __init__(self):
        pass
    
    def chatHandler(self):
        print("chatHandler called")
        pass
    
    def eventHandler(self):
        print("eventHandler called")
        pass
        
    def houseKeeping(self):
        #Called often. Gives the Module a chance to perform various activities without interupting the flow of the program
        pass
    
    def shutdown(self):
        #print("Shutdown called")
        pass