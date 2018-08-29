'''
Created on Aug 21, 2018

@author: paepcke
'''

        
class Message(object):
    def __init__(self, msg_code, state=None):
        self.msg_code = msg_code
        self.state    = state