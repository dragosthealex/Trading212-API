# -*- coding: utf-8 -*-

"""
tradingAPI.low_level
~~~~~~~~~~~~~~

This module provides the low level functions with the service.
"""

import time
import re
from abc import ABCMeta, abstractmethod
from datetime import datetime
from bs4 import BeautifulSoup

from tradingAPI.exceptions import CredentialsException, BaseExc
from .glob import Glob
from .links import path, urls
from .utils import num, expect, get_pip, send_keys_human, w, click, \
    CFD_ORDER_MODES, format_ccy_price
# exceptions
from tradingAPI import exceptions
import selenium.common.exceptions
from selenium.webdriver.chrome.options import Options
from selenium import webdriver

# logging
import logging
logger = logging.getLogger('tradingAPI.low_level')


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


class Movement(object):
    """class-storing movement"""
    def __init__(self, product, quantity, buy_sell, price):
        self.product = product
        self.quantity = quantity
        self.buy_sell = buy_sell
        self.price = price


class OpenPositionWindow(metaclass=ABCMeta):
    """Class for new position modal window"""
    def __init__(self, api, name, order_mode):
        self.api = api
        self.name = name
        self.buy_sell = None
        self.order_mode = order_mode
        self.order_control = None
        self.state = 'initialized'
        self.insfu = False
        self.quantity = 0

    def open(self):
        """Open the new position modal and search for the product

        Opens a "new position" window, looks for the name and selects it

        Args:
            name_counter (str): Ticker name
        """

        """open the new position window"""
        if self.api.css1(path['add-mov']).is_displayed():
            self.api.css1(path['add-mov']).click()
        else:
            self.api.css1('span.dataTable-no-data-action').click()
        logger.debug("opened new position window")
        # Type in the product
        self.api.css1(path['search-box']).send_keys(self.name)
        # Search and check we have something
        result = self.get_result(0)
        if result is None:
            self.close()
            raise exceptions.ProductNotFound(self.name)
        click(result)
        if self.api.is_css("div.widget_message"):
            self.decode(self.api.css1("div.widget_message"))
        self.state = 'open'
        # Set the quantity order control element
        self.set_order_control()

    @abstractmethod
    def set_order_control(self):
        """Set order control div"""
        pass

    def _check_open(self):
        if self.state == 'open':
            return True
        else:
            raise exceptions.WindowException()

    def close(self):
        """Close the window"""
        self._check_open()
        self.api.css1(path['close']).click()
        self.state = 'closed'
        logger.debug(f'closed window for new position in {self.name}')

    def confirm(self):
        """confirm the movement"""
        self._check_open()
        self.get_price()
        if not self.quantity or not self.buy_sell:
            raise ValueError('Quantity and buy/sell has to be set')
        self.api.css1(path['confirm-btn'], self.order_control).click()
        widg = self.api.css("div.widget_message")
        if widg:
            self.decode(widg[0])
            raise exceptions.WidgetException(widg)
        if all(x for x in ['quantity', 'buy_sell'] if hasattr(self, x)):
            self.api.movements.append(Movement(
                self.name, self.quantity, self.buy_sell, self.price))
            logger.info(f'{self.quantity} x {self.name} @ {self.price}'
                        f' PLACED')
        self.state = 'conclused'
        logger.debug('confirmed movement')

    def get_result(self, n=0):
        """Get nth result from instruments search, indexed from 0

        Args:
            n (int): nth result to return

        Returns:
            (mixed): bs4 element if found, None otherwise
        """
        evalxpath = path['res'] + f"[{n + 1}]"
        try:
            instrument = self.api.xpath(evalxpath)[0]
            return instrument
        except Exception:
            return None

    def set_limit(self, category, limit_mode, value):
        """set limit in movement window"""
        self._check_open()
        if (limit_mode not in ["unit", "value"] or category
                not in ["gain", "loss", "both"]):
            raise ValueError()
        if not hasattr(self, 'stop_limit'):
            self.stop_limit = {'gain': {}, 'loss': {}}
            logger.debug("initialized stop_limit")
        if category == 'gain':
            self.api.xpath(
                path['limit-gain-%s' % limit_mode])[0].fill(str(value))
        elif category == 'loss':
            self.api.xpath(
                path['limit-loss-%s' % limit_mode])[0].fill(str(value))
        if category != 'both':
            self.stop_limit[category]['mode'] = limit_mode
            self.stop_limit[category]['value'] = value
        elif category == 'both':
            self.api.xpath(
                path['limit-gain-%s' % limit_mode])[0].fill(str(value))
            self.api.xpath(
                path['limit-loss-%s' % limit_mode])[0].fill(str(value))
            for cat in ['gain', 'loss']:
                self.stop_limit[cat]['mode'] = limit_mode
                self.stop_limit[cat]['value'] = value
        logger.debug("set limit")

    def decode(self, message):
        """decode text pop-up"""
        title = self.api.css1("div.title", message).text
        text = self.api.css1("div.text", message).text
        if title == "Insufficient Funds":
            self.insfu = True
        elif title == "Maximum Quantity Limit":
            raise exceptions.MaxQuantLimit(num(text))
        elif title == "Minimum Quantity Limit":
            raise exceptions.MinQuantLimit(num(text))
        logger.debug("decoded message")

    def decode_update(self, message, value, mult=0.1):
        """decode and update the value"""
        try:
            msg_text = self.api.css1("div.text", message).text
            return num(msg_text)
        except Exception:
            if msg_text.lower().find("higher") != -1:
                value += value * mult
                return value
            else:
                self.decode(message)
                return None

    def set_buy_sell(self, buy_sell):
        """Set buy or sell

        Args:
            mode (str): 'buy' or 'sell'
        """
        self._check_open()
        if buy_sell not in ['buy', 'sell']:
            raise ValueError('mode needs to be "buy" or "sell"')
        self.api.css1(path[buy_sell + '-btn']).click()
        self.buy_sell = buy_sell
        logger.debug(f'buy_sell set to {buy_sell}')

    def get_quantity(self):
        """Return current quantity

        Returns:
            (float): Current quantity
        """
        self._check_open()
        quant = int(self.api.css1(path['quantity'], self.order_control)
                    .get_property('value'))
        self.quantity = quant
        return quant

    def set_quantity(self, quant):
        """Set current quantity

        Args:
            quant (float): Quantity to set
        """
        self._check_open()
        quant_input = self.api.css1(path['quantity'], self.order_control)
        quant_input.clear()
        quant_input.send_keys(quant)
        self.quantity = quant
        logger.debug(f'quantity set: {self.name} to {quant}')

    def get_price(self, mode='buy'):
        """get current price"""
        if mode not in ['buy', 'sell']:
            raise ValueError()
        self._check_open()

        price = format_ccy_price(self.api.css1(
                f'div.buy-sell-control-container div.{mode}-price'
        ).text)
        self.price = price
        return price


class PurePosition(object):
    """class-storing position"""
    def __init__(self, product, quantity, buy_sell, price):
        self.product = product
        self.quantity = quantity
        self.buy_sell = buy_sell
        self.price = price

    def __repr__(self):
        return ' - '.join([str(self.product), str(self.quantity),
                           str(self.buy_sell), str(self.price)])


class LowLevelAPI(object):
    """low level api to interface with the service"""
    def __init__(self):
        self.positions = []
        self.movements = []
        self.stocks = []
        # init globals
        Glob()

    def launch(self, headless=False):
        """launch browser and virtual display, first of all to be launched

        Returns:
            (bool): True if launched successfully

        Raises:
            BrowserException: If failed to launch
        """
        options = Options()
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--profile-directory=Default')
        options.add_argument('--incognito')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-blink-features=AutomationControlled')
        if headless:
            options.add_argument("--headless")
        try:
            self.browser = webdriver.Chrome(options=options)
            logger.debug('Chromium launched launched')
        except Exception:
            raise exceptions.BrowserException('Chromium', 'failed to launch')
        return True

    def shutdown(self):
        """Close the driver, logging out"""
        try:
            self.browser.close()
        except:
            raise exceptions.BrowserException('Chromium', "not started")
        return True

    def css(self, css_path, dom=None):
        """css find function abbreviation"""
        dom = dom if dom else self.browser
        return expect(dom.find_elements_by_css_selector, args=[css_path])

    def css1(self, css_path, dom=None):
        """return the first value of self.css"""
        dom = dom if dom else self.browser
        return self.css(css_path, dom)[0]

    def search_names(self, name, dom=None):
        """Return list of elements matching name passed

        Args:
            name (str): Name of the html element
            dom (WebElement): DOM element, defaults to root

        Returns:
            (list <WebElement>): List of matching elements
        """
        dom = dom if dom else self.browser
        return expect(dom.find_elements_by_name, args=[name])

    def search_name(self, name, dom=None):
        """Return first result by name"""
        dom = dom if dom else self.browser
        return self.search_names(name, dom)[0]

    def xpath(self, xpath, dom=None):
        """xpath find function abbreviation"""
        dom = dom if dom else self.browser
        return expect(dom.find_elements_by_xpath, args=[xpath])

    def is_css(self, css_path, dom=None):
        """Check if there is an element by CSS path

        Returns:
            (bool) True if element is present in dom
        """
        dom = dom if dom else self.browser
        return len(self.css(css_path, dom)) > 0

    def is_xpath(self, xpath, dom=None):
        """Check if there is an element by Xpath

        Returns:
            (bool) True if element is present in xpath
        """
        dom = dom if dom else self.browser
        return len(self.xpath(xpath, dom)) > 0

    def get(self, url):
        """Connect to the URL through 'GET' request

        Args:
            url (str): URL to connect to

        Raises:
            (WebDriverException): If connection timed out
        """
        try:
            w()
            logger.debug(f'visiting {url}')
            self.browser.get(url)
            logger.debug(f'connected to {url}')
            w()
        except selenium.common.exceptions.WebDriverException:
            logger.critical('connection timed out')
            raise

    def wait_for_element(self, css_path):
        """Wait for a css path to appear

        Useful to check popups/modals after navigating to a new url

        Returns:
            (mixed): Element if it appears, false otherwise
        """
        timeout = time.time() + 4
        while not self.is_css(css_path):
            if time.time() > timeout:
                return False
        return self.css1(css_path)

    def login(self, username, password, trading_mode='invest', is_live=False):
        """Login onto the platform, navigating to desired mode

        Args:
            username (str): Plaintext username
            password (str): Plaintext password
            mode (str): 'cfd', 'invest', 'isa'. Default 'invest'
            live (bool): Whether live trading or demo. Default False

        Returns:
            (bool): True if login successful, otherwise False
        """
        # Access login page
        url = urls['login']
        self.get(url)
        try:
            username_input = self.search_name("login[username]")
            pass_input = self.search_name("login[password]")
            # Fill input
            send_keys_human(username_input, username)
            send_keys_human(pass_input, password)
            click(self.css1(path['login-submit']))

            # define a timeout for logging in, checking each second
            timeout = time.time() + 30
            while not self.is_css(path['logo']):
                if time.time() > timeout:
                    logger.critical("login failed")
                    raise CredentialsException(username)
                time.sleep(1)
            logger.info(f'logged in as {username}')

            # Navigate on corresponding mode
            self.go_to_mode(trading_mode, is_live)

            self._post_login_checks(is_live)
        except Exception as e:
            logger.critical("login failed")
            raise BaseExc(e)
        return True

    def _post_login_checks(self, is_live=False):
        """Do checks for modals after login"""
        # check if it's a weekend
        if not is_live and datetime.now().isoweekday() in range(5, 8):
            alert_box = self.wait_for_element(path['alert-box'])
            if alert_box:
                click(alert_box)
                logger.debug("weekend trading alert-box closed")
        # Check new account modal
        new_acc_modal = self.wait_for_element(path['new-acc-modal'])
        if new_acc_modal:
            click(new_acc_modal)

    def go_to_mode(self, trading_mode='invest', is_live=False):
        """Navigate to desired mode of trading

        Args:
            mode (str): 'cfd', 'invest', 'isa'. Default 'invest'
            is_live (bool): Whether live trading or demo. Default False

        Returns:
            (bool): True if navigated successfully
        """
        if is_live:
            self.get(url=urls['live'])
            self.is_live = True
        else:
            self.get(url=urls['demo'])
            self.is_live = False

        if trading_mode == 'cfd':
            pass
        elif trading_mode == 'invest':
            pass
        elif trading_mode == 'isa':
            pass
        else:
            raise BaseExc(f'Invalid mode: {mode}')
        # Do modal checks again
        self._post_login_checks(is_live)
        self.trading_mode = trading_mode
        return True

    def get_bottom_info(self, info):
        """Get information regarding current status

        Args:
            info (str): Information piece. Choose from 'free_funds',
                'blocked_funds', 'account_value', 'live_result', 'used_margin'.
                'used_margin' only for CFD page

        Returns:

        """
        accepted_values = {
            'free_funds': 'equity-free',
            'blocked_funds': 'equity-blocked',
            'account_value': 'equity-total',
            'live_result': 'equity-ppl',
            'used_margin': 'equity-margin'}
        try:
            info_label = accepted_values[info]
            val = self.css1(f'div#{info_label} span.equity-item-value').text
            return num(val)
        except KeyError as e:
            raise exceptions.BaseExc(e)

    class OpenCFDPositionWindow(OpenPositionWindow):
        """add movement window"""
        def __init__(self, api, name, order_mode):
            """Init a modal window for opening position

            Args:
                api:
                name:
                order_mode:
            """
            if order_mode not in list(CFD_ORDER_MODES):
                raise ValueError(f'Order mode invalid for {name}')
            super().__init__(api=api, name=name, order_mode=order_mode)

        def set_order_control(self):
            """Set order control div"""
            if self.order_mode not in CFD_ORDER_MODES:
                raise ValueError(f'invalid order mode: {self.order_mode}')
            order_control_css = f'{self.order_mode.lower()}-order'
            (self.api.xpath(f"//span[@data-tab='{order_control_css}']")[0]
             .click())
            self.order_control = self.api.css1(f'#{order_control_css}')

        def get_mov_margin(self):
            """Get the margin information"""
            self._check_open()
            if self.order_mode == CFD_ORDER_MODES.MARKET:
                return format_ccy_price(self.api.css1('div.order-costs',
                                                      self.order_control).text)
            return 0

        def get_unit_value(self):
            """get unit value of stock based on margin, memoized"""
            # find in the collection
            try:
                unit_value = Glob().theCollector.collection['unit_value']
                unit_value_res = unit_value[self.name]
                logger.debug("unit_value found in the collection")
                return unit_value_res
            except KeyError:
                logger.debug("unit_value not found in the collection")
            pip = get_pip(mov=self)
            quant = 1 / pip
            if hasattr(self, 'quantity'):
                old_quant = self.quantity
            self.set_quantity(quant)
            # update the site
            time.sleep(0.5)
            margin = self.get_mov_margin()
            logger.debug(f"quant: {quant} - pip: {pip} - margin: {margin}")
            if 'old_quant' in locals():
                self.set_quantity(old_quant)
            unit_val = margin / quant
            self.unit_value = unit_val
            Glob().unit_valueHandler.add_val({self.name: unit_val})
            return unit_val

    def new_cfd_pos_window(self, name, order_mode):
        """factory method pattern"""
        return self.OpenCFDPositionWindow(self, name, order_mode)

    class Position(PurePosition):
        """position object"""
        def __init__(self, api, html_div):
            """initialized from div"""
            self.api = api
            if isinstance(html_div, type('')):
                self.soup_data = BeautifulSoup(html_div, 'html.parser')
            else:
                self.soup_data = html_div
            product = self.soup_data.select("td.name")[0].text
            quantity = num(self.soup_data.select("td.quantity")[0].text)
            if ("direction-label-buy" in
                    self.soup_data.select("td.direction")[0].span['class']):
                mode = 'buy'
            else:
                mode = 'sell'
            price = num(self.soup_data.select("td.averagePrice")[0].text)

            # Init parent
            super().__init__(product, quantity, mode, price)

            self.margin = num(self.soup_data.select("td.margin")[0].text)

            self.id = self.find_id()

        def update(self, soup):
            """update the soup"""
            self.soup_data = soup
            return soup

        def find_id(self):
            """find pos ID with with given data"""
            pos_id = self.soup_data['id']
            self.id = pos_id
            return pos_id

        @property
        def close_tag(self):
            """obtain close tag"""
            return f"#{self.id} div.close-icon"

        def close(self):
            """close position via tag"""
            self.api.css1(self.close_tag).click()
            try:
                self.api.xpath(path['ok_but'])[0].click()
            except selenium.common.exceptions.ElementNotInteractableException:
                if (self.api.css1('.widget_message div.title').text ==
                        'Market Closed'):
                    logger.error("market closed, position can't be closed")
                    raise exceptions.MarketClosed()
                raise exceptions.WidgetException(
                    self.api.css1('.widget_message div.text').text)
                # wait until it's been closed
            # set a timeout
            timeout = time.time() + 10
            while self.api.is_css(self.close_tag):
                time.sleep(0.1)
                if time.time() > timeout:
                    raise TimeoutError("failed to close pos %s" % self.id)
            logger.debug("closed pos %s" % self.id)

        def get_gain(self):
            """get current profit"""
            gain = num(self.soup_data.select("td.ppl")[0].text)
            self.gain = gain
            return gain

        def bind_mov(self):
            """bind the corresponding movement"""
            logger = logging.getLogger("tradingAPI.low_level.bind_mov")
            mov_list = [x for x in self.api.movements
                        if x.product == self.product and
                        x.quantity == self.quantity and
                        x.mode == self.buy_sell]
            if not mov_list:
                logger.debug("fail: mov not found")
                return None
            else:
                logger.debug("success: found movement")
            for x in mov_list:
                # find approximate price
                max_roof = self.price + self.price * 0.01
                min_roof = self.price - self.price * 0.01
                if min_roof < x.price < max_roof:
                    logger.debug("success: price corresponding")
                    # bind mov
                    self.mov = x
                    return x
                else:
                    logger.debug("fail: price %f not corresponding to %f" %
                                 (self.price, x.price))
                    continue
            # if nothing, return None
            return None

    def new_pos(self, html_div):
        """factory method pattern"""
        pos = self.Position(self, html_div)
        pos.bind_mov()
        self.positions.append(pos)
        return pos
