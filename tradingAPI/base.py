import json

from tradingAPI.utils import ORDER_STATUS, ORDER_TYPES, CFD_ORDER_TYPES


class Serializable(object):
    """Mixin that provides to_json method."""
    def to_json(self):
        data = {
            'cls': self.__class__.__name__,
            'fields': self.__dict__
        }

        def json_func(value):
            if isinstance(value, Serializable):
                return json.loads(value.to_json())
            return str(value)

        return json.dumps(data, default=json_func)

    @staticmethod
    def from_dict(dict_data, class_name):
        return class_name(**dict_data)

    def to_dict(self):
        return self.__dict__

    def __repr__(self):
        return json.dumps(self.__dict__, default=lambda o: str(o))


class Stock(object):
    """base class for stocks"""
    def __init__(self, product):
        self.product = product
        self.market = True
        self.records = []

    def new_rec(self, rec):
        """add a record"""
        self.records.append(rec)
        return self.records


class Instrument(Serializable):
    """Class storing an instrument"""
    def __init__(self, name, short_name, symbol, exchange=None,
                 fractional=False):
        self.name = name
        self.short_name = short_name
        self.symbol = symbol
        self.exchange = exchange
        self.fractional = fractional


class Order(Serializable):
    """Class storing an order

    Exchange ID is retrieved after it has been placed if it's e.g. pending
    API ID = (direction|symbol|qty|price|time)

    Will use API ID to retrieve a newly placed order
    """
    def __init__(self, instrument, quantity, price, direction, order_type, cost,
                 timestamp):
        """

        Args:
            instrument:
            quantity:
            price:
            direction:
            order_type:
            cost:
            timestamp (datetime.datetime): Time when order was created
        """
        self.instrument = instrument
        self.quantity = quantity
        self.direction = direction
        self.price = price
        self.cost = cost
        self.order_type = order_type
        self.status = ORDER_STATUS.PLACING
        self.exchange_id = None
        self.api_id = self.get_api_id()

    def get_api_id(self):
        """Calculates API ID from attributes

        Returns:
            (str): API ID
        """
        return json.dumps([self.direction.upper(), self.instrument.symbol,
                           self.quantity, self.price])


class CFDMarketOrder(Order):
    def __init__(self, instrument, quantity, price, direction, order_type, cost,
                 timestamp, take_profit=None, stop_loss=None):
        super().__init__(instrument, quantity, price, direction, order_type,
                         cost, timestamp)
        self.take_profit = take_profit
        self.stop_loss = stop_loss


class InvestMarketOrder(Order):
    def __init__(self, instrument, quantity, price, direction, order_type, cost,
                 timestamp, by_value=None):
        """

        Args:
            instrument:
            quantity:
            price:
            direction:
            order_type:
            cost:
            timestamp:
            by_value:
        """
        super().__init__(instrument, quantity, price, direction, order_type,
                         cost, timestamp)
        self.by_value = by_value


# Map order classes to types
# TODO: more of these
ORDER_CLASS_MAP = {
    ORDER_TYPES.MARKET: InvestMarketOrder,
    ORDER_TYPES.LIMIT: Order,
    ORDER_TYPES.STOP: Order,
    ORDER_TYPES.STOP_LIMIT: Order,
    CFD_ORDER_TYPES.MARKET: CFDMarketOrder,
    CFD_ORDER_TYPES.LIMIT_STOP: Order,
    CFD_ORDER_TYPES.OCO: Order,
}


class PurePosition(object):
    """class-storing position"""
    def __init__(self, product, quantity, direction, price):
        self.product = product
        self.quantity = quantity
        self.direction = direction
        self.price = price

    def __repr__(self):
        return ' - '.join([str(self.product), str(self.quantity),
                           str(self.direction), str(self.price)])
