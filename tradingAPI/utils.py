# -*- coding: utf-8 -*-

"""
tradingAPI.utils
~~~~~~~~~~~~~~

This module provides utility functions.
"""
import datetime
import os
import time
import re
from collections import namedtuple

import numpy as np

from tradingAPI import exceptions
from .glob import Glob

# logging
import logging
logger = logging.getLogger('tradingAPI.utils')


# Constants
CfdOrderTypes = namedtuple('CfdOrderTypes', ['MARKET', 'LIMIT_STOP', 'OCO'])
CFD_ORDER_TYPES = CfdOrderTypes('MARKET', 'LIMIT_STOP', 'OCO')
OrderTypes = namedtuple('OrderTypes', ['MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'])
ORDER_TYPES = OrderTypes('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')
OrderStatus = namedtuple('OrderStatus', ['PLACING', 'PLACED', 'FILLED',
                                         'PART_FILLED', 'CANCELLED'])
ORDER_STATUS = OrderStatus('PLACING', 'PLACED', 'FILLED', 'PART_FILLED',
                           'CANCELLED')
TradingModes = namedtuple('TradingModes', ['CFD', 'INVEST', 'ISA'])
TRADING_MODES = TradingModes('CFD', 'INVEST', 'ISA')

BUY = 'buy'
SELL = 'sell'

# Directories
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

INVEST_INSTRUMENTS_CSV = os.path.join(DATA_DIR, 'INVEST_instruments.csv')
ISA_INSTRUMENTS_CSV = os.path.join(DATA_DIR, 'ISA_instruments.csv')
CFD_INSTRUMENTS_CSV = os.path.join(DATA_DIR, 'CFD_instruments.csv')


def expect(func, args, times=7, sleep_t=0.5):
    """try many times as in times with sleep time"""
    while times > 0:
        try:
            return func(*args)
        except Exception as e:
            times -= 1
            logger.debug("expect failed - attempts left: %d" % times)
            time.sleep(sleep_t)
            if times == 0:
                raise exceptions.BaseExc(e)


def num(string):
    """convert a string to float"""
    if not isinstance(string, type('')):
        raise ValueError(type(''))
    try:
        string = re.sub('[^a-zA-Z0-9\.\-]', '', string)
        number = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", string)
        return float(number[0])
    except Exception as e:
        logger = logging.getLogger('tradingAPI.utils.num')
        logger.debug("number not found in %s" % string)
        logger.debug(e)
        return None


def get_number_unit(number):
    """get the unit of number"""
    n = str(float(number))
    mult, submult = n.split('.')
    if float(submult) != 0:
        unit = '0.' + (len(submult)-1)*'0' + '1'
        return float(unit)
    else:
        return float(1)


def get_pip(mov=None, api=None, name=None):
    """get value of pip"""
    # ~ check args
    if mov is None and api is None:
        logger.error("need at least one of those")
        raise ValueError()
    elif mov is not None and api is not None:
        logger.error("mov and api are exclusive")
        raise ValueError()
    if api is not None:
        if name is None:
            logger.error("need a name")
            raise ValueError()
        mov = api.new_pos_window(name)
        mov.open()
    if mov is not None:
        mov._check_open()
    # find in the collection
    try:
        logger.debug(len(Glob().theCollector.collection))
        pip = Glob().theCollector.collection['pip']
        if name is not None:
            pip_res = pip[name]
        elif mov is not None:
            pip_res = pip[mov.product]
        logger.debug("pip found in the collection")
        return pip_res
    except KeyError:
        logger.debug("pip not found in the collection")
    # ~ vars
    records = []
    intervals = [10, 20, 30]

    def _check_price(interval=10):
        timeout = time.time() + interval
        while time.time() < timeout:
            records.append(mov.get_price())
            time.sleep(0.5)

    # find variation
    for interval in intervals:
        _check_price(interval)
        if min(records) == max(records):
            logger.debug("no variation in %d seconds" % interval)
            if interval == intervals[-1]:
                raise TimeoutError("no variation")
        else:
            break
    # find longer price
    for price in records:
        if 'best_price' not in locals():
            best_price = price
        if len(str(price)) > len(str(best_price)):
            logger.debug("found new best_price %f" % price)
            best_price = price
    # get pip
    pip = get_number_unit(best_price)
    Glob().pipHandler.add_val({mov.product: pip})
    return pip


def w_type():
    """Waits a few ms between each typed character"""
    time.sleep(np.random.uniform(0.1, 0.15))


def w():
    """Watis a few more ms - between each activity"""
    time.sleep(np.random.uniform(0.2, 0.3))


def send_keys_human(element, string):
    """Send keys to a WebElement input waiting some time between"""
    w()
    element.clear()
    for ch in string:
        w_type()
        element.send_keys(ch)


def click(element):
    """Click an element, waiting before and after

    Args:
        element (WebElement): DOM element
    """
    w()
    element.click()
    w()


def format_float(text) -> float or None:
    """Format prices read as text with ccy in front of them

    Args:
        text (str): String with prices

    Returns:
        (float): The price as float
    """
    text = re.sub(r'[^0-9.]', '', text)
    if not text:
        return None
    return float(text)


def get_timestamp():
    return datetime.datetime.now()
