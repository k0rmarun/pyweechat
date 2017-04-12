from pyweechat import WeeChatSocket
from pprint import pprint

w = WeeChatSocket()
w.connect()
w.send_async("sync irc.robustirc.#icannotexist")
w.send_async("hdata buffer:gui_buffers(*) full_name")
w.on("buffer_line_added", lambda x: pprint(x))
try:
    while True:
        ret = w.poll()
        if ret is not None:
            pprint(vars(ret), width=200, indent=4)
            pprint(ret.get_hdata_result())
            data = input("Command:")
            w.send_async(data)
except KeyboardInterrupt:
    pass
w.disconnect()