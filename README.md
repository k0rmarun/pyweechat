# pyweechat
Python library for communicating with an weechat irc relay.

## Note
This library is currently in alpha. Expect everything to change one day.

## Usage

<pre>
from pyweechat import WeeChat
from pprint import pprint

w = WeeChat(hostname="localhost", port=8000, use_ssl=False)
w.connect(password=None, compressed=True)
w.send("sync irc.robustirc.#icannotexist")
try:
    while True:
        ret = w.poll()
        if ret:
            pprint(vars(ret))
except KeyboardInterrupt:
    pass
w.disconnect()
</pre>