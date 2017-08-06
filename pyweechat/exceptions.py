class WeeChatUnknownCommandException(Exception):
    """
    Raised when client attempts to send a command which cannot be handled by weechat relay
    """
    def __init__(self, command):
        super(Exception, self).__init__(command)