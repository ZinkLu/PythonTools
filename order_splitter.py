# -*- coding: utf-8 -*-
import json
from collections import Iterable, namedtuple, defaultdict
from copy import deepcopy
from itertools import groupby
from logging import getLogger
from operator import itemgetter

from six.moves import filter, filterfalse
from six.moves.reprlib import repr

_logger = getLogger(__name__)


class DummyDimension(object):
    __slots__ = ()


class Dimension(object):
    __slots__ = ("fields", "_key_value_obj")

    def __init__(self, *fields):
        """
        :param fields: list[str] 不同维度的group
        >>> data = [{"name": 1, "type": 1}, {"name": 2, "type": 1}, {"name": 3, "type": 2}]
        >>> dim = Dimension("type")
        >>> g = dim.iter_group(data)
        >>> g_name, g_value = next(g)
        >>> g_name
        dimension(type=1)
        >>> list(g_value) == [{"name": 1, "type": 1}, {"name": 2, "type": 1}]
        True
        >>> g_name, g_value = next(g)
        >>> g_name
        dimension(type=2)
        >>> list(g_value) == [{"name": 3, "type": 2}]
        True
        """
        self.fields = list(fields)
        self._key_value_obj = namedtuple("dimension", fields)
        object.__init__(self)

    def group(self, data):
        """
        根据不同维度分组
        :param data:
        :type data: list
        :return: 根据fields分组的数据
        """
        try:
            sorted_data = sorted(data, key=itemgetter(*self.fields))
            grouped_data = groupby(sorted_data, itemgetter(*self.fields))
            return grouped_data
        except KeyError:
            raise KeyError(u"没有找到拆单维度条件")

    def iter_group(self, data):
        """
        更加友好地迭代group过的数据
        :param data:
        :return: (namedtuple ,  <groupby-instance>)
        """
        _data = self.group(data)
        for values, g in _data:
            values = values if isinstance(values, Iterable) else (values,)
            yield self._key_value_obj(*values), g


class BaseCondition(object):
    _formal_parameter_name = "x"

    is_true_condition = False

    __slots__ = ()

    def __hash__(self):
        return hash(True)

    def __len__(self):
        return 1

    def __str__(self):
        return "<Condition {}>".format(True)

    def __repr__(self):
        return self.__str__()

    @property
    def real_condition(self):
        return "True"

    @property
    def python_expression(self):
        return "True"

    def to_key(self, x):
        """
        将condition对象转换为 类似于 filter(key=) 的函数
        :param x: 形参, 如果针对每个可迭代对象的
        :return: bool
        """
        try:
            return eval(self.python_expression)
        except Exception as e:
            _logger.exception(e)
            return False

    def apply(self, data):
        """
        将condition应用于过滤对象
        :param data: 需要过滤的数据, 这个数据不能是一个生成器, 否则可能造成问题过滤不出值的问题
              原因, 两个返回值同时使用一个生成器, 如果迭代任意一个生成器直接造成生成器内容被消耗
        :type data Iterable
        :return: Filter(condition), Filter(not condition)
        """
        data1 = data
        if iter(data) is data:
            # 这种情况表示data只能被迭代一次, 会产生数据错误, 使用deepcopy处理
            data1 = deepcopy(data)
            _logger.warning(u"传入了一个迭代器, 使用deepcopy处理")

        return filter(self.to_key, data), filterfalse(self.to_key, data1)

    def is_apply(self, single):
        """判断一个单独的对象, 是否满足当前的粒度划分
        :type single
        :rtype bool
        """
        return self.to_key(single)


class TrueCondition(BaseCondition):
    """
    可以使用 isinstance 进行检查的 TrueCondition 类
    """
    is_true_condition = True


class Condition(BaseCondition):
    __slots__ = ("field", "condition", "extra", "_get_method", "_not_token", "_real_condition")

    def __init__(self, field, condition, get_method=None, **extra):
        """
        >>> condition1 = Condition("name", "startswith('L')")
        >>> condition2 = Condition("age", "< 12")
        >>> condition1.real_condition
        ".startswith('L')"
        >>> condition2.real_condition
        '< 12'
        >>> included, excluded = condition1.apply(data=[{"name": "L1"}, {"name": "Y1"}])
        >>> list(included)
        [{'name': 'L1'}]
        >>> list(excluded)
        [{'name': 'Y1'}]

        :param field: 对应某个字段
        :param condition: 对某个字段的过滤条件
        :param get_method: 默认当做字典处理, 如果传入的是对象, 应该改为 "__getattr__"
        """
        self.field = field
        self.condition = condition
        self.extra = defaultdict(None, **extra)
        self._get_method = get_method or "get"
        self._not_token = False
        self._real_condition = None

    def __hash__(self):
        return hash((self.field, self.condition))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        return "<Condition {0}:{1}>".format(self.field, self.condition)

    @property
    def real_condition(self):
        if self._real_condition is not None:
            return self._real_condition

        condition = self.condition
        if condition.startswith("not "):
            self._not_token = True
            condition = condition.replace("not ", "")
        if "(" in condition and not condition.startswith("."):
            self._real_condition = ".{condition}".format(field=self.field, condition=condition)
        else:
            self._real_condition = "{condition}".format(field=self.field, condition=condition)
        return self._real_condition

    @property
    def python_expression(self):
        """
        返回可以被eval的字符串, 如 x.get("name").startswith("x"), 更加安全的做法应该是判断get出来的对象是否有该方法
        :return:
        """
        return "({not_flag} {param}.{method}('{field}'))".format(not_flag="not" if self._not_token else "",
                                                                 param=self._formal_parameter_name,
                                                                 method=self._get_method,
                                                                 field=self.field) + self.real_condition


class Granularity(BaseCondition):
    """condition的集合, 形成粒度条件, 粒度的不同条件之间必须使用`并且(and)`的条件关联, 和Condition有一样的API"""
    __slots__ = ("conditions", "extra")

    def __init__(self, *conditions, **extra):
        """
        >>> condition1 = Condition("name", "startswith('L')")
        >>> condition2 = Condition("age", "< 12")
        >>> g = Granularity(condition1, condition2)
        >>> included, excluded = g.apply(data=[{"name": "L1", "age": 13}, {"name": "Y1", "age": 12}])
        >>> list(included) == []
        True
        >>> list(excluded) == [{"name": "L1", "age": 13}, {"name": "Y1", "age": 12}]
        True

        :param conditions: Condition1, Condition2, ...
        """
        self.conditions = conditions
        self.extra = defaultdict(None, **extra)
        object.__init__(self)

    def __hash__(self):
        return hash((condition for condition in self.conditions))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __len__(self):
        return len(self.conditions)

    def __str__(self):
        return "<Condition {}>".format(repr(self.conditions))

    @classmethod
    def from_json(cls, json_data, **extra):
        """
        将Json转化为粒度
        :param json_data:{field1: condition1, field2: condition2, field2: condition3}
        :return: Granularity
        """
        dict_data = json.loads(json_data)
        return cls.from_dict(dict_data, **extra)

    @classmethod
    def from_dict(cls, dict_data, **extra):
        """
        :param dict_data: {field1: condition1, field2: condition2, field2: condition3}
        :return: Granularity
        """
        res = list()
        for field, str_condition in dict_data.items():
            res.append(Condition(field=field, condition=str_condition))
        return cls(*res, **extra)

    @property
    def real_condition(self):
        """useless"""
        python_expression_list = [(condition.field, condition.real_condition) for condition in self.conditions]
        return python_expression_list

    @property
    def python_expression(self):
        """连接所有的condition, condition1 and condition2 and ..., 不可以使用or连接"""
        python_expression_list = [condition.python_expression for condition in self.conditions]
        return " and ".join(python_expression_list)


class OrderSplitter(object):
    """
    # 拆单助手, 让拆单更加方便!

    1. 两个重要的概念:
        1. 维度: 将订单以一些维度拆分, 等于按照某些字段分组
        2. 粒度: 对每个维度拆分单订单继续拆分
    2. example:
        - 维度: 订单类型
        - 粒度: 商品编码以C开头
        - 这里的 **类型** 就是维度, 订单可以按照多个维度去分组, 而 **商品编码** 是一个粒度, 他可以运用在所有分组中

    """
    __slots__ = ("dimensions", "granularity", "split_mode")

    def __init__(self, dimension=None, granularities=None, split_mode="remains"):
        """
        :param dimension Dimension
        :param granularities [Granularity, ..], 也可以只传一个颗粒度
        :param split_mode  enum[remains, full]
            - remaining
               如果你的 granularities 是这样传进来的 [Condition(name, startswith(L)), Condition(age, < 12)],
               那么在过滤的时候会无视这两个条件的交集部分, 按照顺序过滤, 因此, 粒度应该区分的越细越好
               |-------------------------|--------------------------------------|-----------------|-------------------|
               |  yield  startswith(L)   |                             not startswith(L)                              |  first filter
               |                         | yield not startswith(L) and age < 12 | not startswith(L) and not age < 12  |  second filter
               |                         |                                      |     yield x     |       not x       |  ohter filter
               |                         |                                      |                 |      remains      |  last time
               如果你需要以上条件的过滤, 可以使用`.apply()`方法调用多次
               Condition(name, startswith(L)).apply(data)
               Condition(age, < 12).apply(data)
               或者使用full的切分方式

            - full
               每次都是用全量数据来运用粒度条件, 最后返回所有数据
               如果你的 granularities 是这样传进来的 [Condition(name, startswith(L)), Condition(age, < 12)],
               |-------------------------|--------------------------------------|-----------------|-------------------|
               |  yield  startswith(L)   |                                                                            |  first filter
               |                          yield  age < 12                     |                                       |  second filter
               |                                                       |                    yield x                   |  ohter filter
               |                                               full                                                   |  last time
        :type split_mode str
        :type dimension Dimension
        :type granularities list[BaseCondition] or BaseCondition
        """
        self.dimensions = dimension

        if granularities is not None:
            if not isinstance(granularities, Iterable):
                granularities = [granularities]

        granularities.sort(key=lambda x: len(x))  # 按照粒度大小排序, 并且添加一个True作为最后过滤的条件
        granularities.append(TrueCondition())
        self.granularity = granularities
        self.split_mode = split_mode

    def _apply_granularity(self, data):
        unfiltered = data
        for gra in self.granularity:
            if self.split_mode == "remains":
                filtered, unfiltered = gra.apply(unfiltered)
                yield filtered, gra
            else:
                filtered, unfiltered = gra.apply(data)
                yield filtered, gra

    def apply_dimensions(self, data):
        """
        :return: generator (namedtuple ,  <groupby-instance>)
        """
        if self.dimensions is None:
            return DummyDimension(), data
        return self.dimensions.iter_group(data)

    def apply_granularity(self, data):
        """
        这个函数需要特别说明, 对属于应用 粒度条件
        由于粒度条件可能是一个列表, 因此我们从粒度最大(condition最多)的开始应用, 随后递减应用, 知道所有的data都已经应用完毕,
        :param data:
        :return: generator
        """
        if self.granularity is None:
            return data

        return self._apply_granularity(data)

    def split(self, data):
        """
        先应用维度, 再应用粒度对data进行分组
        :return: 分好组的明细行(没有分组信息)
        """
        res = list()
        for group, grouped_data in self.apply_dimensions(data):
            if grouped_data:
                for filtered, gra in self.apply_granularity(grouped_data):
                    res.append(list(filtered))
        return res

    def iter_split(self, data):
        """
        迭代友好的方法,
        每次都返回一个元组
        :return: generator ( dimensions_info: namedtuple, Granularity: BaseCondition, grouped_data: grouped_object )
        """
        for dim_info, grouped_data in self.apply_dimensions(data):
            if grouped_data:
                for filtered, gra in self.apply_granularity(grouped_data):
                    yield dim_info, gra, filtered

    def add_dimension(self, *dim):
        """
        添加一个维度
        :param dim: str
        :return:
        """
        if self.dimensions is None:
            self.dimensions = Dimension(*dim)
            return
        self.dimensions.fields.extend(dim)

    def add_granularity(self, gra):
        """
        添加一个粒度
        :param gra: 粒度对象
        :type gra BaseCondition
        :return:
        """
        if self.granularity is None:
            self.granularity = [gra]
            return
        self.granularity.append(gra)
        self.granularity.sort(key=lambda x: len(x))

    def full_apply_to(self, single):
        """返回单条记录匹配的所有粒度"""
        for gra in filter(predicate=lambda x: x.is_apply(single), iterable=self.granularity[:-1]):
            yield gra

    def apply_to(self, single):
        """返回第一个匹配粒度"""
        try:
            return next(self.full_apply_to(single))
        except StopIteration:
            return None
