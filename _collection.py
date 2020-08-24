# -*- coding: utf-8 -*-

from collections import OrderedDict

empty = object()


class NoEmptyDict(dict):
    def __setitem__(self, key, value):
        """如果值是empty就不要设置了"""
        if value is empty:
            return
        super(NoEmptyDict, self).__setitem__(key, value)

    def __missing__(self, key):
        """取不到值则返回empty"""
        return empty


class NullDict(dict):
    """
    如果设置了None值作为value, 则自动转化为'null', 方便格式化sql使用
    """
    def __setitem__(self, key, value):
        if value is None:
            value = "null"

        return super(NullDict, self).__setitem__(key, value)

    def update(self, __m, **kwargs):
        pass


class MappingList(list):
    """拥有字典的特性, 但是可以被序列化成列表, 方便数据format;
       mapping list 将无法删除数据,因为列表元素变化则字典内的地址全部混乱
    """
    def __init__(self, *args, **kwargs):
        self._map = OrderedDict()  # _map的value永远是数字, 代表着真正值在self中的index
        self._trash = empty
        if args:
            raise Exception("The Mapping list only accept keyword args")
        super(MappingList, self).__init__()

        for key, value in kwargs.items():
            self.key_append(key, value)

    def setdefault(self, key, default):
        try:
            index = self._map[key]
            return self[index]
        except KeyError:
            self.key_append(key, default)
            return default

    def items(self):
        return zip(self._map.keys(), self)

    def trash_setdefault(self, key, default, trash_flag=None):
        """如果Key是Trash_Flag, 设置Trash并返回, 否则调用setdefault
        trash 是否会造成循环引用??
        """
        if key is trash_flag:
            if self._trash is empty:
                self._trash = default
            return self._trash
        return self.setdefault(key, default)

    def get(self, key, default=None):
        try:
            return self[self._map[key]]
        except KeyError:
            return default

    def force_get(self, key):
        """
        raise keyError when the key don't exit
        """
        return self[self._map[key]]

    def key_append(self, key, value):
        """append when key does't exist;
           replace the value when key exist;
        """
        try:
            index = self._map[key]
            self[index] = value
        except KeyError:
            # call list append to append
            super(MappingList, self).append(value)
            self._map[key] = self.__len__() - 1

    def to_dict(self):
        """change to dict"""
        if len(self._map) != len(self):
            raise Exception("The mapping has been changed")
        return OrderedDict(zip(self._map.keys(), self))

    def append(self, obj):
        raise Exception("Use .key_append() to set a key-value")

    def extend(self, iterable):
        raise Exception("Use .update() to merge a key-value")

    def update(self, __m, **kwargs):
        for key, value in __m.items():
            self.key_append(key, value)
        for key, value in kwargs.items():
            self.key_append(key, value)

    def popitem(self):
        """pop the last element"""
        ele = super(MappingList, self).pop()
        self._map.popitem(last=True)
        return ele

    def insert(self, index, p_object):
        raise Exception("Use .key_append() to set a key-value")

    def pop(self, *indexes):
        raise Exception("MappingList can't been change")

    def remove(self, value):
        raise Exception("MappingList can't been change")

    def reverse(self):
        raise Exception("MappingList can't been change")

    def sort(self, cmp=None, key=None, reverse=False):
        raise Exception("MappingList can't been change")


if __name__ == '__main__':
    a = MappingList(a=1, b=2)
    a.popitem()
    print(a)
    print(a._map)
    a.to_dict()
