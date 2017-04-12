import pyweechat
from pprint import pprint

w = pyweechat.WeeChatSocket()
w.connect()
pprint(vars(w.send("ping")))
