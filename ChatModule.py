import os
import uuid
import thread
from robotModule import robotModule
from io import BytesIO #For handling the mp3 in memory
from gtts import gTTS #'pip install gTTS' and 'pip install urllib3'
import pygame #pip install pygame
#also requires 'sudo apt-get install python-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev   libsdl1.2-dev libsmpeg-dev python-numpy subversion libportmidi-dev ffmpeg libswscale-dev libavformat-dev libavcodec-dev' on raspberry pi
#Way too many dependencies on raspberry pi. May look at other mp3 player libraries later
class ChatModule(robotModule):
    
    def __init__(self):
        super(ChatModule, self).__init__()
        self.userDict = {}
    
    def chatHandler(self, args):
        super(ChatModule, self).chatHandler()
        self.logger.debug("Chat Module is handling chat message")
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
        
    def replaceWords(self, message):
        message = message.lower()
        message = message.replace('cat','feline')
        message = message.replace('dog','another cat')
        message = message.replace('vvvv','i am a monster truck')
        message = message.replace('wwww','i am a monster truck')
        message = message.replace('kitty','zoe')
        message = message.replace('destroy','construct')
        message = message.replace('kill','pet')
        message = message.replace('fuck','windows 95')
        return message
        
        
    def say(self, message):
        try:
            self.logger.info("Chat message {}".format(message))
            pygame.init()
            message = self.replaceWords(message)
            message.encode('ascii')
            tts = gTTS(message)
            mp3FileDes = BytesIO()
            tts.write_to_fp(mp3FileDes)
            mp3FileDes.seek(0)
            pygame.mixer.music.load(mp3FileDes)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): 
                pygame.time.Clock().tick(10)
            self.logger.debug("Finished playing chat message")
        except UnicodeEncodeError:
            self.logger.debug("Message: {} contains non ascii characters".format(message))
        except Exception:
            self.logger.warning("Chat crash occurred.")

if __name__ == '__main__':
    m = ChatModule()
    m.say('Test')
    m.say('This is a test')
    m.say('This is a test of the emergency alert system')
