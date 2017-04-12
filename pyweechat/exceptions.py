class WeeChatUnknownCommandException(Exception):
    def __init__(self, command):
        super(Exception, self).__init__(command)