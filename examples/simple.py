from pyweechat import WeeChat
from pprint import pprint

w = WeeChat()
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