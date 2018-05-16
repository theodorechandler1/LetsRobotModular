import tempfile
import os
import uuid
import thread
from robotModule import robotModule
import platform

class ChatModule(robotModule):
    
    def __init__(self, voice = "male", voiceNo = 1):
        super(ChatModule, self).__init__()
        self.tempDir = tempfile.gettempdir()
        print("Temporary directory: {}".format(self.tempDir))
        self.voice = voice
        self.voiceNo = voiceNo
        self.hardwareNumber = 0
        self.__findHardwareNo__()
        self.userDict = {}
    
    def chatHandler(self, args):
        super(ChatModule, self).chatHandler()
        print("Chat Module is handling chat message")
        message = args['message']
        user = args['name']
        msgWithoutRobotName = message.split(']')[1:]
        if len(msgWithoutRobotName) >= 1:
            msgWithoutRobotName = msgWithoutRobotName[0]
        else:
            msgWithoutRobotName = ''
        msgWithoutRobotName = msgWithoutRobotName.strip()
        #Command Check
        if msgWithoutRobotName.startswith('.'):
            self.handleCommand(msgWithoutRobotName, user)
        else:
            self.handleChatMessage(msgWithoutRobotName, user)

    def handleChatMessage(self, message, user):
            #Custom Voice Check
            if user in self.userDict:
                print("Found user in dictionary")
                thread.start_new_thread(self.say, (message, self.userDict[user]['voice'], self.userDict[user]['voiceNo']))
            else:
                thread.start_new_thread(self.say, (message,))
    
    def handleCommand(self, command, user):
        if user not in self.userDict:
            self.userDict[user] = {'voice' : 'Male', 'voiceNo' : 1}
        #Get rid of the period
        command = command[1:]
        if len(command) > 1:
            command = command.lower()
            command = command.split()
            #If the command is at least elements long and the first one starts with voice
            if len(command) >= 2 and command[0] == 'voice':
                if command[1] == 'female':
                    self.userDict[user]['voice'] = 'female'
                elif command[1] == 'male':
                    self.userDict[user]['voice'] = 'male'
                else:
                    if len(command) == 3 and command[1] == 'number':
                        self.userDict[user]['voiceNo'] = int(command[2])
                    pass
            elif user == 'trc202' and command[0] == 'shutdown':
                self.say('Shutting down in 10 seconds')
                os.system('sudo shutdown -h 10')
            elif user == 'trc202' and command[0] == 'reboot':
                self.say('Rebooting now')
                os.system('sudo reboot')
            else:
                pass
            
    def removeBannedWords(self, message):
        message.toUpper().replace('lex', '')
        
    def say(self, message, voice = None, voiceNo = None):
        if voice is None:
            voice = self.voice
        if voiceNo is None:
            voiceNo = self.voiceNo
        
        tempFilePath = os.path.join(self.tempDir, "text_" + str(uuid.uuid4()))
        f = open(tempFilePath, "w")
        f.write(message)
        f.close()
        # espeak tts
        if voice == "male":
            result = os.system('cat ' + tempFilePath + ' | espeak --stdout | aplay -D plughw:%d,0' % self.hardwareNumber)
        else:
            result = os.system('cat ' + tempFilePath + ' | espeak -ven-us+f%d -s170 --stdout | aplay -D plughw:%d,0' % (voiceNo, self.hardwareNumber))
        os.remove(tempFilePath)
        return result
        
    def __findHardwareNo__(self):
        if 'windows' not in platform.system().lower():
            for hardwareNumber in (2, 0, 3, 1, 4):
                self.hardwareNumber = hardwareNumber
                result = self.say(" ")
                if result == 0:
                    print("Found hardware number {}".format(hardwareNumber))
                    self.hardwareNumber = hardwareNumber
                    break

if __name__ == '__main__':
    m = ChatModule(voice = "Female", voiceNo = 3)
    m.say('Test')
    m.say('This is a test')
    m.say('This is a test of the emergency alert system')