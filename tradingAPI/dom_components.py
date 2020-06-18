from abc import ABCMeta, abstractmethod

import logging

import time

import selenium
from bs4 import BeautifulSoup

from tradingAPI import exceptions
from tradingAPI.base import CFDMarketOrder, InvestMarketOrder, ORDER_CLASS_MAP
from tradingAPI.exceptions import ParsingException
from tradingAPI.links import dommap
from tradingAPI.utils import (click, CFD_ORDER_TYPES, format_float,
                              num, ORDER_TYPES, w, get_timestamp, BUY,
                              TRADING_MODES, ORDER_STATUS)

logger = logging.getLogger('tradingAPI.low_level')


class OrderWindow(metaclass=ABCMeta):
    """Class for new position modal window"""
    def __init__(self, api, instrument, order_type):
        self.api = api
        self.name = instrument
        self.instrument = instrument
        self.direction = None
        self.quantity = None
        self.cost = None
        self.price = None
        self.order_type = order_type
        self.order_control = None
        self.state = 'initialized'
        self.insfu = False

    def open(self):
        """Open the new position modal and search for the product"""
        self.state = 'opening'
        if self.api.css1(dommap['add-mov']).is_displayed():
            self.api.css1(dommap['add-mov']).click()
        else:
            self.api.css1('span.dataTable-no-data-action').click()
        logger.debug("opened new position window")
        # Type in the product
        self.api.css1(dommap['search-box']).send_keys(self.instrument)
        # Search and check we have something
        result = self.get_result(0)
        if result is None:
            self.close()
            raise exceptions.ProductNotFound(self.instrument)
        click(result)
        if self.api.is_css("div.widget_message"):
            self.decode(self.api.css1("div.widget_message"))
        self.state = 'open'
        # Set the quantity order control element
        self.set_order_control()

    def set_order_control(self):
        """Set order control div"""
        order_control_css = f'{self.order_type.lower()}-order'
        (self.api.xpath(f"//span[@data-tab='{order_control_css}']")[0]
         .click())
        self.order_control = self.api.css1(f'#{order_control_css}')

    def _check_open(self):
        if self.state == 'open' or self.state == 'opening':
            return True
        else:
            raise exceptions.WindowException()

    def close(self):
        """Close the window"""
        self._check_open()
        self.api.css1(dommap['close']).click()
        self.state = 'closed'
        logger.debug(f'closed window for new position in {self.instrument}')

    @abstractmethod
    def confirm(self) -> bool:
        pass

    @abstractmethod
    def get_price(self) -> float:
        pass

    def get_result(self, n=0):
        """Get nth result from instruments search, indexed from 0

        Args:
            n (int): nth result to return

        Returns:
            (mixed): bs4 element if found, None otherwise
        """
        evalxpath = dommap['res'] + f"[{n + 1}]"
        try:
            instrument = self.api.xpath(evalxpath)[0]
            return instrument
        except Exception:
            return None

    def set_limit(self, category, limit_mode, value):
        """TODO: set limit in movement window"""
        self._check_open()
        if (limit_mode not in ["unit", "value"] or category
                not in ["gain", "loss", "both"]):
            raise ValueError()
        if not hasattr(self, 'stop_limit'):
            self.stop_limit = {'gain': {}, 'loss': {}}
            logger.debug("initialized stop_limit")
        if category == 'gain':
            self.api.xpath(
                dommap['limit-gain-%s' % limit_mode])[0].fill(str(value))
        elif category == 'loss':
            self.api.xpath(
                dommap['limit-loss-%s' % limit_mode])[0].fill(str(value))
        if category != 'both':
            self.stop_limit[category]['mode'] = limit_mode
            self.stop_limit[category]['value'] = value
        elif category == 'both':
            self.api.xpath(
                dommap['limit-gain-%s' % limit_mode])[0].fill(str(value))
            self.api.xpath(
                dommap['limit-loss-%s' % limit_mode])[0].fill(str(value))
            for cat in ['gain', 'loss']:
                self.stop_limit[cat]['mode'] = limit_mode
                self.stop_limit[cat]['value'] = value
        logger.debug("set limit")

    def check_widget_message(self):
        """Check whether there is any error message

        Raises:
            (exceptions.WidgetException): If there's any error
        """
        widg = self.api.css("div.widget_message", self.order_control)
        if widg:
            self.decode(widg[0])
            raise exceptions.WidgetException(widg)

    def decode(self, message):
        """decode text pop-up"""
        text = message.text.strip()
        if 'you have funds to' in text:
            self.insfu = True
        elif 'maximum remaining quantity' in text:
            raise exceptions.MaxQuantLimit(num(text))
        elif 'minimum' in text:
            raise exceptions.MinQuantLimit(num(text))
        logger.debug("decoded message")

    def get_quantity(self) -> float:
        """Return current quantity

        Returns:
            (float): Current quantity
        """
        self._check_open()
        quant = int(self.api.css1(dommap['quantity'], self.order_control)
                    .get_property('value'))
        self.quantity = quant
        return quant

    def set_quantity(self, quant):
        """Set current quantity

        Args:
            quant (float): Quantity to set
        """
        self._check_open()
        quant_input = self.api.css1(dommap['quantity'], self.order_control)
        quant_input.clear()
        quant_input.send_keys(quant)
        self.quantity = quant
        logger.debug(f'quantity set: {self.instrument} to {quant}')

    def post_order_placement(self, order):
        # Append to API placed orders
        self.api.orders.append(order)
        logger.debug(f'{self.quantity} x {self.instrument} @ {self.price}'
                     f' PLACED')
        self.state = 'conclused'
        logger.debug('confirmed order placed')


class CFDOrderWindow(OrderWindow):
    """add movement window"""

    def __init__(self, api, instrument, order_type):
        """Init a modal window for opening position

        Args:
            api:
            instrument:
            order_type:
        """
        if order_type not in list(CFD_ORDER_TYPES):
            raise ValueError(f'Order mode invalid for {instrument}')
        super().__init__(api=api, instrument=instrument, order_type=order_type)

    def set_direction(self, direction):
        """Set buy or sell

        Args:
            mode (str): 'buy' or 'sell'
        """
        self._check_open()
        if direction not in ['buy', 'sell']:
            raise ValueError('mode needs to be "buy" or "sell"')
        self.api.css1(dommap[direction + '-btn']).click()
        self.direction = direction
        logger.debug(f'direction set to {direction}')

    def get_price(self) -> float:
        """get current price"""
        if self.order_type not in ['buy', 'sell']:
            raise ValueError()
        self._check_open()

        price = format_float(self.api.css1(
                f'div.buy-sell-control-container '
                f'div.{self.order_type}-price'
        ).text)
        self.price = price
        return price

    def get_margin_info(self):
        """Get the margin information"""
        self._check_open()
        if self.order_type == CFD_ORDER_TYPES.MARKET:
            return format_float(self.api.css1('div.order-costs',
                                              self.order_control).text)
        return 0

    def confirm(self) -> bool:
        """Confirms the order placement

        Raises:
            (exceptions.WidgetException): If not able to confirm

        Returns:
            (bool): True if placed
        """
        self._check_open()
        if not self.quantity or not self.direction:
            raise ValueError('Quantity and buy/sell has to be set')

        self.get_price()
        # Calculate cost as price * quantity. For limit will be min cost
        self.cost = self.price * self.quantity
        self.api.css1(dommap['confirm-btn'], self.order_control).click()
        # Check for errors
        self.check_widget_message()
        timestamp = get_timestamp()
        order = CFDMarketOrder(self.instrument, self.quantity, self.price,
                               self.direction, self.order_type, self.cost,
                               timestamp)
        self.post_order_placement(order)
        return True


class InvestOrderWindow(OrderWindow):
    """add movement window"""
    def __init__(self, api, instrument, order_type):
        """Init a modal window for opening position

        Args:
            api (tradingAPI.low_level.API): Api instance
            instrument ():
            order_type (str): Field of ORDER_MODES namedtuple
        """
        if order_type not in list(ORDER_TYPES):
            raise ValueError(f'Order mode invalid for {instrument}')
        super().__init__(api=api, instrument=instrument, order_type=order_type)
        self.by_value = False

    def _toggle_shares_by_value(self, by_value=False):
        """Toggle the switch between value / shares for fractional shares

        Args:
            by_value (bool): Set whether to use by value or not.
                If False, self.set_quantity will use number of shares.
                Otherwise it will use order value
        Returns:
            (bool): True if managed to set, false otherwise
        """
        self.by_value = by_value
        if self.api.is_css('div.invest-by-container.disabled',
                           self.order_control):
            return False

        click(self.api.css1('div.invest-by-content', self.order_control))
        if by_value:
            (self.api.css1('div.item-invest-by-items-value',
                           self.order_control).click())
        else:
            (self.api.css1('div.item-invest-by-items-quantity',
                           self.order_control).click())
        return True

    def confirm(self) -> bool:
        """Confirms the order

        Raises:
            (exceptions.WidgetException): If not able to confirm

        Returns:
            (bool): True if placed
        """
        self._check_open()
        self.cost = self.price * self.quantity
        self.api.css1(dommap['review-order'], self.order_control).click()
        self.check_widget_message()
        self.api.wait_for_element(dommap['send-order'])
        click(self.api.css1(dommap['send-order']))
        self.check_widget_message()
        timestamp = get_timestamp()
        order = InvestMarketOrder(self.instrument, self.quantity, self.price,
                                  BUY, self.order_type, self.cost, timestamp,
                                  self.by_value)
        self.post_order_placement(order)
        return True
        
    def get_price(self):
        """Get current price from window

        Returns:
            (float): Current price
        """
        price = format_float(self.api.css1('#invest-order '
                                               'div.fund-ammount-wrapper').text)
        self.price = price
        return price

    def set_quantity(self, quant, by_value=False):
        """Override for fractional shares

        NOTICE! order may be filled with a different quantity than what we
        calculate now.

        Args:
            quant (float): Number of shares or amount of money
            by_value (bool): If True, use quant to specify value of the order,
                otherwise quant represents number of shares. Default is False

        If fractional, quantity = value in CCY, so get qty from html
        Otherwise, qty = correct so we need to get the value
        """
        # Toggle by value
        self._toggle_shares_by_value(by_value=by_value)
        if not by_value:
            return super().set_quantity(quant=quant)

        # Otherwise we set the value
        logger.debug(f'quantity BY VALUE')
        super().set_quantity(quant)

        self.quantity = quant / self.get_price()

    def get_quantity(self) -> float:
        """Return current quantity - override for fractional shares

        If we've got by_value set on, we get quantity from price * quantity

        Returns:
            (float): Current quantity
        """
        print("pula")
        if not self.by_value:
            return super().get_quantity()
            # Calculate the approx quantity and set it
        self.quantity= super().get_quantity() / self.get_price()

        return self.quantity


class PendingOrdersTab():

    def __init__(self, api):
        """"""
        self.api = api
        self.div_css = '#ordersTable'

    def open_all_cols(self):
        """Make sure to open all columns"""

    def get(self):
        """Get the parent div"""
        if self.api.is_css(self.div_css):
            return self.api.css1(self.div_css)
        return False

    def activate(self):
        """Activate the table if not open already"""
        self.api.close_all()
        if not self.get():
            self.api.css1('span.tab-item.taborders').click()
            self.api.wait_for_element(self.div_css)

    def load_orders(self):
        """Load all the orders into Order objects"""

        orders = []
        for order_element in self.api.css('tbody tr', self.get()):
            try:
                orders.append(self._decode_order_element(order_element))
            except (RuntimeError, IndexError)as e:
                raise ParsingException('Order', e)
        return orders

    def _decode_order_element(self, el):
        """Decode an order WebElement into corresponding order

        Args:
            el (selenium.WebElement): The <tr> order element

        Returns:
            (Order): Order instance
        """
        # Get the instrument from short name
        short_name = self.api.css1('td.name', el).text
        instrument = self.api.get_instrument(short_name=short_name)
        # Get the Exchange ID
        exchange_id = self.api.css1('td.humanId').text
        direction = self.api.css1('td.direction').text
        order_type = self._parse_order_type(self.api.css1('td.type').text)
        quantity = format_float(self.api.css1('td.quantity').text)
        cost = format_float(self.api.css1('td.value').text)
        price = format_float(self.api.css1('td.currentPrice').text)
        timestamp = self.api.css1('td.created').text
        # stop limit
        limit = stop = None
        if self.api.is_css('span.stop-limit-order-data-limit-price'):
            limit = format_float(self.api.css1('span.stop-limit-order-'
                                               'data-limit-price').text)
            stop = format_float(self.api.css1('span.stop-limit-order-'
                                              'data-limit-price').text)

        order_cls = ORDER_CLASS_MAP[order_type]
        order = order_cls(instrument=instrument, quantity=quantity, price=price,
                          direction=direction, order_type=order_type, cost=cost,
                          timestamp=timestamp)
        # If we found order here it means status is placed
        order.status = ORDER_STATUS.PLACED
        order.exchange_id = exchange_id

        # Depending on order type add extra stuff
        if cost:
            # Means Market Invest/ISA order
            order.by_value = True
            order.quantity = order.cost / order.price
        else:
            order.cost = order.quantity * order.price
        if limit:
            order.limit = limit
        if stop:
            order.stop = stop
        return order

    def _parse_order_type(self, exchange_order_type):
        """Parse order type info from exchange to one of the namedtuple

        Args:
            exchange_order_type (str): Order type string from api

        Returns:
            (str): ORDER_TYPE / CFD_ORDER_TYPE
        """
        if self.api.trading_mode == TRADING_MODES.INVEST:
            mapping = {
               'Market': ORDER_TYPES.MARKET,
               'Limit': ORDER_TYPES.LIMIT,
               'Stop': ORDER_TYPES.STOP,
               'Stop Limit': ORDER_TYPES.STOP_LIMIT
            }
            return mapping[exchange_order_type]
        mapping = {
            'Market': CFD_ORDER_TYPES.MARKET,
            'Stop Limit': CFD_ORDER_TYPES.LIMIT_STOP,
            'OCO': CFD_ORDER_TYPES.OCO
        }
        return mapping[exchange_order_type]












