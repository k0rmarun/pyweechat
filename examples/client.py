from pyweechat import WeeChatClient
from datetime import timedelta


def test():
    print("test")
    client.print()
    return True

client = WeeChatClient()
client.run(test, timedelta(0, 0, 0, 100))
