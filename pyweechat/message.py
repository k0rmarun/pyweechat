import zlib


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
        assert self.length == len(self.data) + 4

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
            ppaths = []
            for j in range(path_length):
                ppaths.append(self.read_pointer())

            path_data = {}
            path_data["__path"] = ppaths
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
        for i in range(count):
            i_count = self.read_int()
            i_name = self.read_string()
            i_type = self.read_type()
            i_items = []
            for j in range(i_count):
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
        if isinstance(_type, bytes):
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