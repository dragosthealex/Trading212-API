# trade121

Python based API for Trading 212 broker using selenium browser automation.

The single best improvement that can be done for portfolio returns is 
diversification. But it can be hard to manually rebalance more than a dozen 
positions by hand, and this is where **trade121** comes in to help.


## Table of Contents

- [Background](#background)
- [Install](#Installing)
    - [Requirements](#Requirements)
- [Usage & Api reference](#Usage)
- [Contributing](#Contributing)
- [Licensing](#Licensing)
- [Acknowledgements](#Acknowledgements)


## Background

The intention of this API is not to enable high-frequency trading or anything 
that might otherwise be 100% impossible for a human. It may be used to automate 
portfolio management and analysis, implement more complex stop/limit orders, 
and any type of activity normally possible through the web UI. 


The API does not directly hit the broker's endpoints, it just simulates human
actions, by clicking the html UI elements (albeit faster). As such, there are 
limitations on how fast can orders be placed or prices be read. Ideally it 
should be used with trading frequency of at least 1 minute

**trade121** supports both *CFD* and *INVEST* accounts, and also the UK-specific
ISA (it's the same as INVEST, with the exception of £20,000 pay-in limit)

## Installing / Getting started

**trade121** uses Seleium with Chrome webdriver to emulate user interaction
with the broker

### Requirements

The dependencies for dev instances are:
- Python>=3.6
- [https://chromedriver.chromium.org/downloads](chromedriver)


To install the API, just install it with pip.

```shell
> pip install trade121
```

## Usage & Api reference

REQUIRED - **SOON**


## Contributing
see [contribute](docs/CONTRIBUTE.md) to participate.

### Setting up Dev

Here's a brief intro about what a developer must do in order to start developing
the project further:

```shell
> git clone https://github.com/dragosthealex/trade121.git
> cd trade121/
> conda create -n env python=3
> activate env
> pip install -r dev-requirements.txt
> python setup.py develop
```

### Versioning

The Semantic Versioning is used in this repository in this format:

    [major].[minor].[patch]-{status}

* **major** indicates incopatible changes
* **minor** indicates new features
* **patch** indicates bug fixies
* **status** show the status (alpha, beta, rc, etc.)

for more information see [Semantic Versioning](http://semver.org/)


## Licensing

This software is under the MIT license.


## Acknowledgements

Initial development was started by [Federico Lolli](https://github.com/federico123579/Trading212-API) 
in 2017, with an API using [pyvirtualdisplay](). While it provided a great start,
there was an opportunity for taking it further and refining it to enable better
interaction. Due to the requirement for X11, it was not possible to run it on 
 Windows. It also needed major updates as the Trading212 website has changed
in the meantime.

