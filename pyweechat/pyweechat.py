import ssl
import socket
import zlib
from datetime import datetime

class WeeChatMessage:
    def __init__(self, data, debug=False):
        self.data = data
        self.length = 0
        self.compression = False
        self.debug = debug

        self.read_length()
        self.decompress()
        self.result = []
        self.id = self.read_string()

        try:
            while len(self.data) > 0:
                self.log("init:", len(self.data))
                self.log("init: remaining", len(self.data), self.data)
                type = self.read_type()
                self.log("init: type", type)
                self.log("init: remaining", len(self.data), self.data)
                _data = self.read_value(type)
                self.result.append(_data)
        except ValueError:
            self.result = None
        except KeyError:
            self.result = None

    def get_hdata_result(self) -> dict:
        if self.result:
            data = self.result[0][2]
            if isinstance(data, list) and len(data) == 1:
                return data[0]
            return data
        return None

    def log(self, *messages):
        if self.debug:
            print(*messages)

    def splice(self, len: int, ignoreLast=False):
        data = self.data[:len]
        self.data = self.data[len + (1 if ignoreLast else 0):]
        self.log("splice: ", len, data)
        return data

    def as_num(self, data):
        self.log("as_num: ", data)
        return sum((c if isinstance(c, int) else ord(c)) << (i * 8) for i, c in enumerate(data[::-1]))

    def read_length(self):
        data = self.as_num(self.splice(4))
        self.log("length", data)
        self.length = data
        assert self.length == len(self.data)+4

    def read_type(self):
        data = self.splice(3)
        self.log("type:", data)
        return data

    def read_chr(self):
        data = self.splice(1)
        self.log("chr:", data)
        return data

    def read_int(self):
        data = self.as_num(self.splice(4))
        self.log("int:", data)
        return data

    def read_long(self):
        len = self.as_num(self.read_chr())
        data = self.splice(len)
        self.log("long:", data)
        return int(data)

    def read_string(self):
        len = self.read_int()
        self.log("string_:", len)
        if len == 0:
            return ""
        elif len == 0xffffffff:
            return ""
        data = self.splice(len)
        self.log("string:", data)
        return data.decode()

    def read_buffer(self):
        data = self.read_string()
        self.log("buffer:", data)
        return data

    def read_pointer(self):
        len = self.as_num(self.read_chr())
        data = self.splice(len)
        self.log("pointer:", len, data)
        return data.decode()

    def read_time(self):
        len = self.as_num(self.read_chr())
        data = self.splice(len)
        self.log("time:", data)
        return datetime.fromtimestamp(float(data))

    def read_hash_table(self):
        key_type = self.read_type()
        value_type = self.read_type()
        count = self.read_int()
        data = {}
        for i in range(count):
            k = self.read_value(key_type)
            v = self.read_value(value_type)
            data[k] = v
        self.log("hashtable", data)
        return data

    def read_hdata(self):
        self.log("begin hdata")
        hpath = self.read_string()
        if not hpath:
            return None
        path_length = len(hpath.split("/"))
        keys = self.read_string()
        keys = keys.split(",")
        _keys = []
        for key in keys:
            _key = key.split(":")
            self.log("hdata: key", _key)
            _keys.append((_key[0], _key[1]))

        count = self.read_int()
        path = []
        for i in range(count):
            for j in range(path_length):
                self.read_pointer()

            path_data = {}
            for key in _keys:
                self.log("hdata: val:", key)
                path_data[key[0]] = self.read_value(key[1])
            path.append(path_data)
        self.log("hdata:", hpath, _keys, path)
        return hpath, _keys, path

    def read_info(self):
        data = self.read_string(), self.read_string()
        self.log("type:", data)
        return data

    def read_infolist(self):
        name = self.read_string()
        count = self.read_int()
        items = {}
        for i in range(len(count)):
            i_count = self.read_int()
            i_name = self.read_string()
            i_type = self.read_type()
            i_items = []
            for j in range(len(i_count)):
                i_items.append(self.read_value(i_type))
            items[i_name] = i_items
        self.log("type:", name, items)
        return name, items

    def read_array(self):
        type = self.read_type()
        count = self.read_int()
        elems = []
        for i in range(count):
            elems.append(self.read_value(type))
        return elems

    def read_value(self, _type):
        funcs = {
            "chr": self.read_chr,
            "int": self.read_int,
            "lon": self.read_long,
            "str": self.read_string,
            "buf": self.read_buffer,
            "ptr": self.read_pointer,
            "tim": self.read_time,
            "htb": self.read_hash_table,
            "hda": self.read_hdata,
            "inf": self.read_info,
            "inl": self.read_infolist,
            "arr": self.read_array
        }
        if isinstance(_type,bytes):
            _type = _type.decode()

        self.log("value", _type)
        if _type in funcs:
            return funcs[_type]()
        raise KeyError(_type)

    def decompress(self):
        self.compression = (self.splice(1) != b"\x00")
        self.log("compression", self.compression)
        if self.compression:
            self.data = zlib.decompress(self.data)
            self.log("decompressed", self.data)


class WeeChatUnknownCommandException(Exception):
    def __init__(self, command):
        super(Exception, self).__init__(command)


class WeeChatSocket:
    def __init__(self, hostname: str = "localhost", port: int = 8000, use_ssl: bool = False):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.load_default_certs()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if use_ssl:
            self.socket = context.wrap_socket(self.socket, server_hostname=hostname)
        self.socket.connect((hostname, port))
        self.socket.setblocking(0)

        self.events = {
            "buffer_opened": None,
            "buffer_type_changed": None,
            "buffer_moved": None,
            "buffer_merged": None,
            "buffer_unmerged": None,
            "buffer_hidden": None,
            "buffer_unhidden": None,
            "buffer_remaned": None,
            "buffer_title_changed": None,
            "buffer_localvar_added": None,
            "buffer_localvar_changed": None,
            "buffer_localvar_removed": None,
            "buffer_closing": None,
            "buffer_cleared": None,
            "buffer_line_added": None,
            "nicklist": None,
            "nicklist_diff": None,
            "pong": None,
            "upgrade": None,
            "upgrade_ended": None,
        }

    def connect(self, password: str = None, compressed: bool = True) -> None:
        conection = b"init"
        if password:
            conection += b" password=" + password.encode("utf-8")
        if compressed is False:
            conection += b" compression=off"
        conection += b"\r\n"
        self.socket.sendall(conection)

    def send_async(self, data: str) -> None:
        if data:
            command = data.strip().split()[0].strip()
            if command not in ["hdata", "info", "infolist", "nicklist", "input", "sync", "desync", "quit"]:
                raise WeeChatUnknownCommandException(command)
            self.socket.sendall(data.encode() + b"\r\n")

    def poll(self) -> WeeChatMessage:
        try:
            response = self.socket.recv(4096*1024)
        except socket.error:
            return None

        if response:
            response = WeeChatMessage(response)
            if response.id:
                id = response.id.decode()
                if id[0] == "_":
                    id = id[1:]
                if id in self.events.keys() and self.events[id] is not None:
                    if response.result and isinstance(response.result, list):
                        for r in response.result:
                            if len(r) > 2:
                                self.events[id](r[2])
            return response
        return None

    def on(self, event: str, callback: callable = None) -> None:
        if event in self.events.keys():
            self.events[event] = callback

    def disconnect(self) -> None:
        self.socket.sendall(b"quit\r\n")
        self.socket.close()

    def wait(self) -> WeeChatMessage:
        while True:
            ret = self.poll()
            if ret is not None:
                return ret

    def send(self, data:str) -> WeeChatMessage:
        self.send_async(data)
        return self.wait()

from pprint import pprint

class WeeChatBuffer:
    def __init__(self, data:dict = None):
        self.name = ""
        self.full_name = ""
        self.short_name = ""
        self.title = ""
        self.active = ""
        self.number = ""
        self.lines = []
        self.nicklist = []
        if data:
            self.name = data.get("name")
            self.full_name = data.get("full_name")
            self.short_name = data.get("short_name")
            self.title = data.get("title")
            self.active = data.get("active")
            self.number = data.get("number")
            self.lines = []
            self.nicklist = []

    @staticmethod
    def from_pointer(socket: WeeChatSocket, pointer: str):
        if not pointer.startswith("gui"):
            pointer = "0x"+pointer

        # read meta information
        resp_buf = socket.send("hdata buffer:" + pointer).get_hdata_result()
        if resp_buf is None:
            return None
        buffer = WeeChatBuffer(resp_buf)

        if resp_buf.get("nicklist") and resp_buf.get("nicklist") != 0:
            resp_nick = socket.send("nicklist "+pointer).get_hdata_result()
            if resp_nick:
                for nick in resp_nick:
                    if nick.get("visible") == b"\x01":
                        buffer.nicklist.append({
                            "name":nick.get("name"),
                            "prefix": nick.get("prefix"),
                            "level": nick.get("level",-1),
                            "group": nick.get("group") == "\x01"
                        })

        def add_line(line):
            buffer.lines.append({
                "message": line["message"],
                "displayed": line["displayed"] == b"\x01",
                "highlight": line["highlight"] == b"\x01",
                "date": line["date"]
            })
        # read line count
        resp_lc = socket.send("hdata buffer:{}/lines".format(pointer)).get_hdata_result()
        if resp_lc is not None:
            line_count = resp_lc.get("lines_count")
            if line_count < 20:  # request all line data at once
                resp_ld = socket.send("hdata buffer:{}/lines/first_line(*)/data").get_hdata_result()
                if resp_ld:
                    for line in resp_ld:
                        add_line(line)
            else: #request a single line at a time
                last_id = resp_lc.get("first_line")
                for i in range(line_count-1):
                    resp_ld = socket.send("hdata line:0x"+last_id+"/data").get_hdata_result()
                    if resp_ld:
                        add_line(resp_ld)

                    resp_next = socket.send("hdata line:0x"+last_id).get_hdata_result()
                    if resp_next:
                        if resp_next.get("next_line") is not None and resp_next.get("next_line") != "0":
                            last_id = resp_next.get("next_line")
                        else:
                            break
                    else:
                        break

        return buffer, resp_buf


class WeeChatClient:
    def __init__(self, **kwargs):
        self.socket = WeeChatSocket(kwargs.get("hostname","localhost"), kwargs.get("port",8000), kwargs.get("use_ssl",False))
        self.socket.connect(kwargs.get("password"), kwargs.get("compressed", True))

        self.buffers = []
        self.setup()
        pprint(self.buffers, indent=4, width=200)

    def setup(self):
        last = "gui_buffers"
        while True:
            buf, raw = WeeChatBuffer.from_pointer(self.socket, last)

            if buf:
                self.buffers.append(buf)
            if raw:
                if raw.get("next_buffer") is not None and raw.get("next_buffer") != "0":
                    last = raw.get("next_buffer")
                else:
                    break

if __name__ == '__main__':
    WeeChatClient()