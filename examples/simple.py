from pyweechat import WeeChatSocket
from pprint import pprint

w = WeeChatSocket()
w.connect()
w.send("sync irc.robustirc.#icannotexist")
try:
    while True:
        ret = w.poll()
        if ret:
            pprint(vars(ret))
except KeyboardInterrupt:
    pass
w.disconnect()