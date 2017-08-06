from .socket import WeeChatSocket


class WeeChatBuffer:
    """
    Represents a single weechat buffer.
    Used in WeeChatClient
    """
    def __init__(self, data: dict = None):
        self.name = ""
        self.full_name = ""
        self.short_name = ""
        self.title = ""
        self.active = ""
        self.number = -1
        self.lines = []
        self.nicklist = []
        self.pointer = None
        if data:
            self.name = data.get("name")
            self.full_name = data.get("full_name")
            self.short_name = data.get("short_name")
            self.title = data.get("title")
            self.active = data.get("active")
            self.number = data.get("number", -1)
            self.lines = []
            self.nicklist = []
            self.pointer = data.get("buffer")

    def add_line(self, line):
        if line:
            self.lines.append({
                "message": line["message"],
                "displayed": line["displayed"] == b"\x01",
                "highlight": line["highlight"] == b"\x01",
                "date": line["date"]
            })

    def add_nick(self, nick):
        if nick and nick.get("visible") == b"\x01":
            self.nicklist.append({
                "name": nick.get("name"),
                "prefix": nick.get("prefix"),
                "level": nick.get("level", -1),
                "group": nick.get("group") == "\x01"
            })

    @staticmethod
    def from_pointer(socket: WeeChatSocket, pointer_: str):
        if not pointer_.startswith("gui"):
            pointer = "0x" + pointer_
        else:
            pointer = pointer_

        # read meta information
        resp_buf = socket.send("hdata buffer:" + pointer).get_hdata_result()
        if resp_buf is None:
            return None
        buffer = WeeChatBuffer(resp_buf)
        buffer.pointer = pointer_

        if resp_buf.get("nicklist") and resp_buf.get("nicklist") != 0:
            resp_nick = socket.send("nicklist " + pointer).get_hdata_result()
            if resp_nick:
                for nick in resp_nick:
                    buffer.add_nick(nick)

        # read line count
        resp_lc = socket.send("hdata buffer:{}/lines".format(pointer)).get_hdata_result()
        if resp_lc is not None:
            line_count = resp_lc.get("lines_count")
            if line_count < 20:  # request all line data at once
                resp_ld = socket.send("hdata buffer:{}/lines/first_line(*)/data").get_hdata_result()
                if resp_ld:
                    for line in resp_ld:
                        buffer.add_line(line)
            else:  # request a single line at a time
                last_id = resp_lc.get("first_line")
                for i in range(line_count - 1):
                    resp_ld = socket.send("hdata line:0x" + last_id + "/data").get_hdata_result()
                    if resp_ld:
                        buffer.add_line(resp_ld)

                    resp_next = socket.send("hdata line:0x" + last_id).get_hdata_result()
                    if resp_next:
                        if resp_next.get("next_line") is not None and resp_next.get("next_line") != "0":
                            last_id = resp_next.get("next_line")
                        else:
                            break
                    else:
                        break

        return buffer, resp_buf
