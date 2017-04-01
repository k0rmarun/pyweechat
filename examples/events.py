from pyweechat import WeeChat
from pprint import pprint

w = WeeChat()
w.connect()
w.send("sync irc.robustirc.#icannotexist")
w.on("buffer_line_added", lambda x: pprint(x))
try:
    while True:
        w.poll()
except KeyboardInterrupt:
    pass
w.disconnect()