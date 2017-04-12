import pyweechat
from pprint import pprint

w = pyweechat.WeeChatSocket()
w.connect()
w.send_async("ping")

try:
    while True:
        ret = w.poll()
        if ret:
            pprint(vars(ret))
except KeyboardInterrupt:
    pass
