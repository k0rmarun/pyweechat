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
        while len(self.data) > 0:
            type = self.read_type()
            _data = self.read_value(type)
            self.result.append(_data)

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
            return b""
        elif len == 0xffffffff:
            return b""
        data = self.splice(len)
        self.log("string:", data)
        return data

    def read_buffer(self):
        data = self.read_string()
        self.log("buffer:", data)
        return data

    def read_pointer(self):
        len = self.as_num(self.read_chr())
        data = self.splice(len)
        self.log("pointer:", len, data)
        return data

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
        keys = self.read_string()
        keys = keys.split(b",")
        _keys = []
        for key in keys:
            _key = key.split(b":")
            self.log("hdata: key", _key)
            _keys.append((_key[0], _key[1]))

        count = self.read_int()
        path = []
        for i in range(count):
            ppath = self.read_pointer()
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
            b"chr": self.read_chr,
            b"int": self.read_int,
            b"lon": self.read_long,
            b"str": self.read_string,
            b"buf": self.read_buffer,
            b"ptr": self.read_pointer,
            b"tim": self.read_time,
            b"htb": self.read_hash_table,
            b"hda": self.read_hdata,
            b"inf": self.read_info,
            b"inl": self.read_infolist,
            b"arr": self.read_array
        }
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


class WeeChat:
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

    def send(self, data: str) -> None:
        if data:
            command = data.strip().split()[0].strip()
            if command not in ["hdata", "info", "infolist", "nicklist", "input", "sync", "desync", "quit"]:
                raise WeeChatUnknownCommandException(command)
            self.socket.sendall(data.encode() + b"\r\n")

    def poll(self) -> WeeChatMessage:
        try:
            response = self.socket.recv(1024)
        except socket.error:
            return

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
