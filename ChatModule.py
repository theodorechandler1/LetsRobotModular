import tempfile
import os
import uuid
import thread
from robotModule import robotModule
import platform
import time
from random import randint

#Helpful espeak options found on https://delightlylinux.wordpress.com/2015/03/23/linux-has-voice-with-espeak/

class ChatModule(robotModule):
    
    def __init__(self):
        super(ChatModule, self).__init__()
        self.tempDir = tempfile.gettempdir()
        #print("Temporary directory: {}".format(self.tempDir))
        self.defaultVoice = "en" #Which voice to use
        self.defaultSpeed = 160 #How fast the text is read
        self.defaultPitch = 50
        self.voiceMinPitch = 10
        self.voiceMaxPitch = 200
        self.voiceMinSpeed = 10
        self.voiceMaxSpeed = 250
        self.userDefaults = {'voice' : self.defaultVoice, 'speed' : self.defaultSpeed, 'pitch' : self.defaultPitch}
        self.hardwareNumber = 0
        #self.__findHardwareNo__()
        self.userDict = {}
        self.availableVoices = ['de', 'default', 'en', 'en-us', 'es-la', 'fr', 'pt', 'croak', 'f1', 'f2', 'f3', 'f4', 'f5', 'klatt', 'klatt2', 'klatt3', 'klatt4', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'whisper', 'whisperf']
    
    def chatHandler(self, args):
        super(ChatModule, self).chatHandler()
        message = args['message']
        user = args['name']
        msgWithoutRobotName = message.split(']')[1:]
        if len(msgWithoutRobotName) >= 1:
            msgWithoutRobotName = msgWithoutRobotName[0]
        else:
            msgWithoutRobotName = ''
        msgWithoutRobotName = msgWithoutRobotName.strip()
        #Command Check
        if msgWithoutRobotName.startswith('!'):
            self.handleCommand(msgWithoutRobotName, user)
        elif msgWithoutRobotName.startswith('.'): #Not a message to speak
            pass
        else: #Not a command. Say it.
            self.handleChatMessage(msgWithoutRobotName, user)

    def handleChatMessage(self, message, user):
        #Custom Voice Check
        if user in self.userDict:
            thread.start_new_thread(self.say, (message, self.userDict[user]['voice'], self.userDict[user]['speed'], self.userDict[user]['pitch']))
        else:
            thread.start_new_thread(self.say, (message,))
    
    def handleCommand(self, command, user):
        if user == 'trc202':
            time.sleep(1)
        #First we make sure the user has a reference in the dictionary
        if user not in self.userDict:
            self.userDict[user] = self.userDefaults.copy()
        #Now we can handle the command
        commandWords = command.split(' ')
        try:
            if commandWords[0] == '!override' and user == 'trc202':
                user = commandWords[1]
                commandWords = commandWords[2:]
                print commandWords
            if commandWords[0] == '!help':
                self.sendCommandList()
            elif commandWords[0] == '!voice':
                self.handleVoiceCommand(commandWords, user)
            elif commandWords[0] == '!fortune':
                fortune = os.popen('fortune').read()
                self.sendMessage(fortune)
                self.handleChatMessage(fortune,'AutoMod')
            else:
                self.sendCommandList()
        except:
            self.sendCommandList()
        print(command)
    
    def getVoiceString(self, user):
        userValues = None
        if user not in self.userDict:
            userValues = self.userDefaults
        else:
            userValues = self.userDict[user]
        return "User: {} has voice: {} with speed: {} and pitch: {}".format(user,userValues['voice'],userValues['speed'], userValues['pitch'])
        
    def handleVoiceCommand(self, commandWords, user):
        if len(commandWords) == 1:
            self.sendMessage(self.getVoiceString(user))
        elif commandWords[1] == 'speed':
            speed = int(commandWords[2])
            if(self.voiceMinSpeed <= speed <= self.voiceMaxSpeed): #Make sure the user selected a value between the min and max
                self.userDict[user]['speed'] = speed
                self.sendMessage("User: {} has set speed: {}".format(user, speed))
            else:
                self.sendMessage("Speed: {} outside of range {}-{}".format(speed, self.voiceMinSpeed, self.voiceMaxSpeed))
        elif commandWords[1] == 'pitch':
            pitch = int(commandWords[2])
            if(self.voiceMinPitch <= pitch <= self.voiceMaxPitch):
                self.userDict[user]['pitch'] = pitch
                self.sendMessage("User: {} has set pitch: {}".format(user, pitch))
            else:
                self.sendMessage("Pitch: {} outside of range {}-{}".format(pitch, self.voiceMinPitch, self.voiceMaxPitch))
        elif commandWords[1] == 'list':
            self.sendMessage(str(self.availableVoices))
        elif commandWords[1] == 'set' and commandWords[2] in self.availableVoices:
            self.userDict[user]['voice'] = commandWords[2]
            self.sendMessage("User: {} has set voice: {}".format(user,self.userDict[user]['voice']))
        elif commandWords[1] == 'add' and commandWords[2] in self.availableVoices:
            self.userDict[user]['voice'] = self.userDict[user]['voice'] + "+" + commandWords[2]
            self.sendMessage("User: {} has set voice: {}".format(user,self.userDict[user]['voice']))
        elif commandWords[1] == 'random':
            self.userDict[user]['voice'] = self.availableVoices[randint(0,len(self.availableVoices))]
            self.sendMessage("User: {} has set voice: {}".format(user,self.userDict[user]['voice']))
        else:
            self.sendCommandList()
    
    def sendCommandList(self):
        commands = ""
        commands += "!help - this command"
        commands += "!voice - lists current voice"
        commands += "!voice speed <{}-{}>- sets voice speed".format(self.voiceMinSpeed, self.voiceMaxSpeed)
        commands += "!voice pitch <{}-{}>- sets voice pitch".format(self.voiceMinPitch, self.voiceMaxPitch)
        commands += "!voice list - Lists the available voices"
        commands += "!voice set <voice> - Sets the user voice from voice list"
        commands += "!voice add <voice> - Adds an additional voice from the list"
        commands += "!voice random - Sets a random voice"
        commands += "!fortune - Get a random fortune"
        self.sendMessage(commands)
        
    def say(self, message, voice = None, speed = None, pitch = None):
        if voice is None:
            voice = self.defaultVoice
        if speed is None:
            speed = self.defaultSpeed
        if pitch is None:
            pitch = self.defaultPitch
        
        tempFilePath = os.path.join(self.tempDir, "text_" + str(uuid.uuid4()))
        f = open(tempFilePath, "w")
        f.write(message)
        f.close()
        # espeak tts
        command = "espeak -s {} -v {} -p {} -f {}  >/dev/null 2>&1".format(speed, voice, pitch, tempFilePath)
        result = os.system(command)
        os.remove(tempFilePath)
        return result

    def sendMessage(self, message):
        maxMessageLength = 128
        if len(message) > maxMessageLength: #Make sure we don't lose any data by exceeding the max message length
            splitLocation = message.rfind(' ', 0, maxMessageLength) #Find the nearest space to split on
            if (splitLocation == -1): #Couldn't find a space (This should never happen)
                splitLocation = maxMessageLength
            #Yay, recursion to save the day!
            self.sendMessage(message[:splitLocation])
            self.sendMessage(message[splitLocation:])
        else:
            super(ChatModule, self).sendMessage("[AutoMod] .{}".format(message))
    
if __name__ == '__main__':
    m = ChatModule()
    m.say('Test')
    m.say('This is a test')
    m.say('This is a test of the emergency alert system')