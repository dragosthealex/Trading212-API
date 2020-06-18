# -*- coding: utf-8 -*-

"""
tradingAPI.links
~~~~~~~~~~~~~~

This module provides info about pathes.
"""

import os.path

dommap = {
    # Login
    'login-submit': 'input.button-login',
    'logo': "div.nav_logo",
    'alert-box': "span.weekend-trading-close",
    'new-acc-modal': r'div.eq-onboarding-popup div.close-icon',
    # Account
    'acc-menu': 'div.account-menu-button',
    'acc-items': 'div.account-types-item',
    # Open Position Window modal
    'add-mov': "span.open-dialog-icon.svg-icon-holder",
    'search-box': "div.searchbox input",
    'res': '//*[@id="list-results-instruments"]/div/div[3]/div/div/div',
    'sell-btn': "div.buy-sell-control-container div.sell-button",
    'buy-btn': "div.buy-sell-control-container div.buy-button",
    'quantity': "div.quantity-slider-input-wrapper input",
    'limit-gain-unit':
        '//*[@id="smartorder"]/div[1]/div[3]/div/div[3]/div[1]/div[5]/input',
    'limit-gain-value':
        '//*[@id="smartorder"]/div[1]/div[3]/div/div[3]/div[1]/div[6]/input',
    'limit-loss-unit':
        '//*[@id="smartorder"]/div[1]/div[3]/div/div[3]/div[3]/div[5]/input',
    'limit-loss-value':
        '//*[@id="smartorder"]/div[1]/div[3]/div/div[3]/div[3]/div[6]/input',
    'confirm-btn': "div.confirm-button",
    'review-order': 'div.review-order-button',
    'send-order': 'div.send-order-button',

    'data-table': "tbody.table-body.dataTable-show-currentprice-arrows",
    'search-btn': "#navigation-search-button",
    'search-pref': "input.search-input",
    'pref-icon': "div.search-results-list-item .search-results-column div",
    'add-btn': "div.search-results-column div.svg-icon-holder",
    'plus-icon': "svg.search-plus-icon",
    'close-prefs': "div.back-button",
    'close': "div.window div.close-icon",
    'movs-table': "div#accountPanel .table-body",
    'ok_but': '//*[contains(@class, "widget_message")]/div[2]/span[1]',
    'stock-table': '//*[@id="tradePanel"]/div[5]/div[3]/div',
    'sent': "span.tradebox-buyers-container.number-box",
    'trade-box': '//div[@id="tradePanel"]/div[5]/div[3]/div[1]' +
        '/div[2]/div[2]/span',
    'back-btn': 'div.back-button',
}

urls = {
    'login': 'http://live.trading212.com/',
    'demo': 'http://demo.trading212.com/',
    'live': r'https://trading212.com/en/login'
}

file_path = {
    'pip': os.path.join(os.path.dirname(__file__), 'data', 'pip.yml'),
    'unit_value': os.path.join(os.path.dirname(__file__),
                               'data', 'unit_value.yml')
}
