# -*- coding: utf-8 -*-

"""
tradingAPI.low_level
~~~~~~~~~~~~~~

This module provides the low level functions with the service.
"""

import time
import os
from datetime import datetime

import pandas as pd
from tradingAPI.base import Instrument
from tradingAPI.dom_components import InvestOrderWindow, \
    CFDOrderWindow, PendingOrdersTab, SearchInstrumentsModal, PositionsTab
from tradingAPI.exceptions import CredentialsException, BaseExc
from .glob import Glob
from .links import dommap, urls
from .utils import num, expect, send_keys_human, w, click, TRADING_MODES, \
    INVEST_INSTRUMENTS_CSV, ISA_INSTRUMENTS_CSV, CFD_INSTRUMENTS_CSV
from tradingAPI import exceptions
import selenium.common.exceptions
from selenium.webdriver.chrome.options import Options
from selenium import webdriver

# logging
import logging
logger = logging.getLogger('tradingAPI.low_level')


class LowLevelAPI(object):
    """low level api to interface with the service"""
    def __init__(self):
        self.positions = {
            TRADING_MODES.CFD: pd.DataFrame(),
            TRADING_MODES.INVEST: pd.DataFrame(),
            TRADING_MODES.ISA: pd.DataFrame()
        }
        self.placed_orders = {
            TRADING_MODES.CFD: pd.DataFrame(),
            TRADING_MODES.INVEST: pd.DataFrame(),
            TRADING_MODES.ISA: pd.DataFrame()
        }
        self.placing_orders = {
            TRADING_MODES.CFD: pd.DataFrame(),
            TRADING_MODES.INVEST: pd.DataFrame(),
            TRADING_MODES.ISA: pd.DataFrame()
        }
        self.instruments = {
            TRADING_MODES.CFD: pd.DataFrame(),
            TRADING_MODES.INVEST: pd.DataFrame(),
            TRADING_MODES.ISA: pd.DataFrame()
        }  # Dataframe with instruments
        self.log = logger
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

    def wait_for_element_disappear(self, css_path):
        """Wait for a css path to disappear

        USeful when closing stuff to wait until animation finishes

        Returns:
            (bool): True if element disappears within timeout, False otherwise
        """
        timeout = time.time() + 4
        while self.is_css(css_path):
            if time.time() > timeout:
                return False
        return True

    def login(self, username, password, trading_mode=TRADING_MODES.INVEST,
              is_live=False, autoload=True):
        """Login onto the platform, navigating to desired mode

        Args:
            username (str): Plaintext username
            password (str): Plaintext password
            mode (str): 'cfd', 'invest', 'isa'. Default 'invest'
            live (bool): Whether live trading or demo. Default False
            autoload (bool): Whether to autoload positions, instruments and
                orders
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
            click(self.css1(dommap['login-submit']))

            # define a timeout for logging in, checking each second
            timeout = time.time() + 10
            while not self.is_css(dommap['logo']):
                if time.time() > timeout:
                    logger.critical("login failed")
                    raise CredentialsException(username)
                time.sleep(1)
            logger.info(f'logged in as {username}')
            self._post_login_checks(is_live)
            # Navigate on corresponding mode
            self.go_to_mode(trading_mode, is_live, autoload)
        except Exception as e:
            logger.critical("login failed")
            raise BaseExc(e)
        return True

    def _post_login_checks(self, is_live=False):
        """Do checks for modals after login"""
        # check if it's a weekend
        if not is_live and datetime.now().isoweekday() in range(5, 8):
            alert_box = self.wait_for_element(dommap['alert-box'])
            if alert_box:
                click(alert_box)
                logger.debug("weekend trading alert-box closed")
        # Check new account modal
        new_acc_modal = self.wait_for_element(dommap['new-acc-modal'])
        if new_acc_modal:
            click(new_acc_modal)

    def go_to_mode(self, trading_mode=TRADING_MODES.INVEST, is_live=False,
                   autoload=True):
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

        # go to the account menu
        self.wait_for_element(dommap['acc-menu'])
        w()
        self.css1(dommap['acc-menu']).click()
        if trading_mode == TRADING_MODES.CFD:
            self.css1(f"{dommap['acc-items']}.cfd").click()
        elif trading_mode == TRADING_MODES.INVEST:
            self.css1(f"{dommap['acc-items']}.equity").click()
        elif trading_mode == TRADING_MODES.ISA:
            self.css1(f"{dommap['acc-items']}.isa").click()
        else:
            raise BaseExc(f'Invalid mode: {mode}')
        self.wait_for_element(dommap['acc-menu'])  # wait until done
        # Do modal checks again
        self._post_login_checks(is_live)
        self.trading_mode = trading_mode
        # Autoload
        # If autoload, reload all pos, instruments
        if autoload:
            self.load_instruments()
            self.load_orders()
            self.load_positions()
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

    def close_all(self):
        """Close any modal window if open"""
        if self.is_css(dommap['close']):
            self.css1(dommap['close']).click()

    def load_orders(self, close=False):
        """Reload and set pending orders, for current trading mode

        Args:
            close (bool): Whether to close window after loading. Default False
        """
        orders_modal = self.new_pending_orders_tab()
        orders_modal.open()
        orders = orders_modal.get_orders(as_df=True)
        if close:
            orders_modal.close()
        new_orders_no = len(orders) - len(self.placed_orders[self.trading_mode])
        self.placed_orders[self.trading_mode] = orders
        self.log.debug(f'Reloading orders: {new_orders_no} new, total'
                       f' {len(orders)}')

    def load_positions(self, close=False):
        """Reload and set pending orders, for current trading mode

        Args:
            close (bool): Whether to close window after loading. Default False
        """
        pos_modal = self.new_positions_tab()
        pos_modal.open()
        pos = pos_modal.get_positions(as_df=True)
        if close:
            pos_modal.close()
        new_pos_no = len(pos) - len(self.positions[self.trading_mode])
        self.positions[self.trading_mode] = pos
        self.log.debug(f'Reloading positions: {new_pos_no} new, total'
                       f' {len(pos)}')

    def load_instruments(self, force_reload=False):
        """Set own instruments list, for the current trading mode

        e.g. if current mode is CFD, will set
        self.instruments[TRADING_MODES.CFD]

        Args:
            force_reload (bool): Whether to force the reload instead of using
                the cahced CSVs
        """
        self.instruments[self.trading_mode] = (
            self.get_all_instruments(force_reload)
        )

    def get_all_instruments(self, force_reload=False):
        """Depending on the trading mode, load instruments available

        """
        if self.trading_mode == TRADING_MODES.INVEST:
            return self._get_refresh_instruments(INVEST_INSTRUMENTS_CSV,
                                                 force_reload)
        if self.trading_mode == TRADING_MODES.CFD:
            return self._get_refresh_instruments(CFD_INSTRUMENTS_CSV,
                                                 force_reload)
        if self.trading_mode == TRADING_MODES.ISA:
            return self._get_refresh_instruments(ISA_INSTRUMENTS_CSV,
                                                 force_reload)

    def _get_refresh_instruments(self, csv_path, force_reload):
        """Loads instruments from csv or forces reload

        Args:
            csv_path (str): Path to store / retrieve from
            force_reload (bool)): If true, do a new search

        Returns:
            (pd.DataFrame): Instruments dataframe
        """
        if os.path.isfile(csv_path) and not force_reload:
            return pd.read_csv(csv_path)
        # Perform a new search of instruments
        instruments_modal = self.new_search_instruments_modal()
        instruments_modal.open()
        instruments = instruments_modal.load_all_instruments()
        # Convert to list of dicts
        instruments = pd.DataFrame([i.to_dict() for i in instruments])
        instruments.to_csv(csv_path, index=False)
        instruments_modal.close()
        return instruments

    def get_instrument(self, short_name=None, symbol=None, name=None):
        """Retrieve an instrument from the list, by shorthand, symbol or name

        Args:
            short_name (str): Short name e.g. Apple
            symbol (str): Ticker e.g. AAPL
            name (str): Full name e.g. Apple Inc.

        Returns:
            (Instrument): The instrument found

        Raises:
            (ValueError): If nothing passed
            (ProductNotFound): If not found the instrument
        """
        if (self.instruments[self.trading_mode] is None or
                self.instruments[self.trading_mode].empty):
            self.load_instruments()
        instrums = self.instruments[self.trading_mode]
        if short_name:
            instrument = instrums.loc[instrums['short_name'] == short_name]
        elif name:
            instrument = instrums.loc[instrums['name'] == name]
        elif symbol:
            instrument = instrums.loc[instrums['symbol'] == symbol]
        else:
            raise ValueError('You must pass at least one identifier')
        if instrument.empty:
            raise exceptions.ProductNotFound(f'{short_name}/{symbol}/{name}')
        return Instrument.from_dict(instrument.iloc[0].to_dict())

    def scroll_to_bottom(self, css_path):
        """Scrolls element to bottom

        Args:
            css_path (str): CSS Selector
        """
        if not self.is_css(css_path):
            raise ValueError(f'Could not find element {css_path}')
        elem = self.css1(css_path)
        old_height = 0

        while int(elem.get_attribute('scrollHeight')) > old_height:
            old_height = int(elem.get_attribute('scrollHeight'))
            self.browser.execute_script(
                f"document.querySelector('{css_path}').scroll(0, {old_height})"
            )
            w()

    def new_search_instruments_modal(self):
        """Instantiate the search window modal"""
        return SearchInstrumentsModal(self)

    def new_cfd_order_window(self, name, order_mode):
        """Instantiate a OpenCFDPositionWindow for opening invest positions

        Args:
            name (str): Name of the instrument. Should be from available names
            order_mode (str): Field of CFD_ORDER_MODES namedtuple

        Returns:
            (OpenCFDPositionWindow) The window instance
        """
        if self.trading_mode != TRADING_MODES.CFD:
            raise ValueError('Cannot open CFD window unless in CFD mode')
        return CFDOrderWindow(self, name, order_mode)

    def new_invest_order_window(self, name, order_mode):
        """Instantiate a OpenInvestPositionWindow for opening invest positions

        Args:
            name (str): Name of the instrument. Should be from available names
            order_mode (str): Field of ORDER_MODES namedtuple

        Returns:
            (OpenInvestPositionWindow) The window instance
        """
        if self.trading_mode != TRADING_MODES.INVEST:
            raise ValueError('Cannot open CFD window unless in CFD mode')
        return InvestOrderWindow(self, name, order_mode)

    def new_pending_orders_tab(self):
        """

        Returns:
            (PendingOrdersTab): The orders window
        """
        return PendingOrdersTab(self)

    def new_positions_tab(self):
        """

        Returns:
            (PositionsTab): The positions window
        """
        return PositionsTab(self)
