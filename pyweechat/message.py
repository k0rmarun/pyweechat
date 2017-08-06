import zlib
from datetime import datetime

class WeeChatMessage:
    """
    Response data of the weechat relay server
    """
    def __init__(self, data, debug=False):
        """
        Parse the response data from a weechat relay server
        Detects if response is compressed and decompresses it.
        Set result to none if error during parse.
        :param data: data to parse. Must not be streamed.
        :param debug: write debug information?

        Usage:
        >>> response = WeeChatMessage(data).result
        >>> main_hadata = WeeChatMessage(data).get_hdata_result()
        """
        self.data = data
        self.length = 0
        self.compression = False
        self.debug = debug

        self._read_length()
        self._decompress()
        self.result = []
        self.id = self._read_string()

        try:
            while len(self.data) > 0:
                self._log("init:", len(self.data))
                self._log("init: remaining", len(self.data), self.data)
                type = self._read_type()
                self._log("init: type", type)
                self._log("init: remaining", len(self.data), self.data)
                _data = self._read_value(type)
                self.result.append(_data)
        except ValueError:
            self.result = None
        except KeyError:
            self.result = None

    def get_hdata_result(self) -> dict:
        """
        Return only the main hdata block.
        :return: main hdata block
        """
        if self.result:
            data = self.result[0][2]
            if isinstance(data, list) and len(data) == 1:
                return data[0]
            return data
        return None

    def _log(self, *messages):
        """
        Condition debug log
        :param messages: data to log
        """
        if self.debug:
            print(*messages)

    def _splice(self, len: int, ignoreLast=False):
        """
        Take first len bytes from remaining data
        :param len:
        :param ignoreLast:
        :return:
        """
        data = self.data[:len]
        self.data = self.data[len + (1 if ignoreLast else 0):]
        self._log("_splice: ", len, data)
        return data

    def _as_num(self, data):
        """
        Interpret data as a hex encoded number
        :param data:
        :return:
        """
        self._log("_as_num: ", data)
        return sum((c if isinstance(c, int) else ord(c)) << (i * 8) for i, c in enumerate(data[::-1]))

    def _read_length(self):
        """
        Read length of received message
        :return:
        """
        data = self._as_num(self._splice(4))
        self._log("length", data)
        self.length = data
        assert self.length == len(self.data) + 4

    def _read_type(self):
        """
        Read type of next data object
        :return: str
        """
        data = self._splice(3)
        self._log("type:", data)
        return data

    def _read_chr(self):
        """
        Read a single character
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_char
        :return: byte
        """
        data = self._splice(1)
        self._log("chr:", data)
        return data

    def _read_int(self):
        """
        Read a single fixed size number
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_integer
        :return: int
        """
        data = self._as_num(self._splice(4))
        self._log("int:", data)
        return data

    def _read_long(self):
        """
        Read a dynamic sized number
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_long_integer
        :return: int
        """
        len = self._as_num(self._read_chr())
        data = self._splice(len)
        self._log("long:", data)
        return int(data)

    def _read_string(self):
        """
        Read a string
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_string
        :return: str
        """
        len = self._read_int()
        self._log("string_:", len)
        if len == 0:
            return ""
        elif len == 0xffffffff:
            return ""
        data = self._splice(len)
        self._log("string:", data)
        return data.decode()

    def _read_buffer(self):
        """
        Read a buffer
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_buffer
        :return: str
        """
        data = self._read_string()
        self._log("buffer:", data)
        return data

    def _read_pointer(self):
        """
        Read a pointer
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_pointer
        :return: str
        """
        len = self._as_num(self._read_chr())
        data = self._splice(len)
        self._log("pointer:", len, data)
        return data.decode()

    def _read_time(self):
        """
        Read a time object
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_time
        :return: datetime
        """
        len = self._as_num(self._read_chr())
        data = self._splice(len)
        self._log("time:", data)
        return datetime.fromtimestamp(float(data))

    def _read_hash_table(self):
        """
        Read a hashtable
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_hashtable
        :return: dict
        """
        key_type = self._read_type()
        value_type = self._read_type()
        count = self._read_int()
        data = {}
        for i in range(count):
            k = self._read_value(key_type)
            v = self._read_value(value_type)
            data[k] = v
        self._log("hashtable", data)
        return data

    def _read_hdata(self):
        """
        Read a hdata object
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_hdata
        :return: tuple(str, list, list)
        """
        self._log("begin hdata")
        hpath = self._read_string()
        if not hpath:
            return None
        path_length = len(hpath.split("/"))
        keys = self._read_string()
        keys = keys.split(",")
        _keys = []
        for key in keys:
            _key = key.split(":")
            self._log("hdata: key", _key)
            _keys.append((_key[0], _key[1]))

        count = self._read_int()
        path = []
        for i in range(count):
            ppaths = []
            for j in range(path_length):
                ppaths.append(self._read_pointer())

            path_data = {}
            path_data["__path"] = ppaths
            for key in _keys:
                self._log("hdata: val:", key)
                path_data[key[0]] = self._read_value(key[1])
            path.append(path_data)
        self._log("hdata:", hpath, _keys, path)
        return hpath, _keys, path

    def _read_info(self):
        """
        Read an info object
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_info
        :return: tuple(str, str)
        """
        data = self._read_string(), self._read_string()
        self._log("type:", data)
        return data

    def _read_infolist(self):
        """
        Read list of info objects
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_infolist
        :return: list(tuple(str,str))
        """
        name = self._read_string()
        count = self._read_int()
        items = {}
        for i in range(count):
            i_count = self._read_int()
            i_name = self._read_string()
            i_type = self._read_type()
            i_items = []
            for j in range(i_count):
                i_items.append(self._read_value(i_type))
            items[i_name] = i_items
        self._log("type:", name, items)
        return name, items

    def _read_array(self):
        """
        Read a list of objects of same type
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#object_array
        :return: list
        """
        type = self._read_type()
        count = self._read_int()
        elems = []
        for i in range(count):
            elems.append(self._read_value(type))
        return elems

    def _read_value(self, _type):
        """
        Read value from key
        See https://weechat.org/files/doc/devel/weechat_relay_protocol.en.html#objects
        :param _type: id of value type
        :return: any
        """
        funcs = {
            "chr": self._read_chr,
            "int": self._read_int,
            "lon": self._read_long,
            "str": self._read_string,
            "buf": self._read_buffer,
            "ptr": self._read_pointer,
            "tim": self._read_time,
            "htb": self._read_hash_table,
            "hda": self._read_hdata,
            "inf": self._read_info,
            "inl": self._read_infolist,
            "arr": self._read_array
        }
        if isinstance(_type, bytes):
            _type = _type.decode()

        self._log("value", _type)
        if _type in funcs:
            return funcs[_type]()
        raise KeyError(_type)

    def _decompress(self):
        """
        Detect weather remaining data is compressed and decompress
        :return:
        """
        self.compression = (self._splice(1) != b"\x00")
        self._log("compression", self.compression)
        if self.compression:
            self.data = zlib.decompress(self.data)
            self._log("decompressed", self.data)