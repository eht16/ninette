# Ninette

[![PyPI](https://img.shields.io/pypi/v/ninette.svg)](https://pypi.org/project/ninette/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ninette.svg)](https://pypi.org/project/ninette/)
[![License](https://img.shields.io/pypi/l/ninette.svg)](https://pypi.org/project/ninette/)


A simple alerting system to get notified about important events or news.

Ninette generates alerts as email messages or by executing a command
(which could generate a Signal, Jabber, Matrix, SMS, ... message) to inform about
important events or news in your region.

It can be used as an alternative or addition to smart phone apps which create push notifications.
With the Command alerter, any form of notification can be used.

Currently supported alert providers are:
**NINA** (service of the German disaster control organization) and
**Tagesschau** (German television news service).

More providers can be added easily.


## Features

  * Alerts from German **Bundesamt für Bevölkerungsschutz**
    (NINA API via https://nina.api.bund.dev, including events from DWD, MOWAS, Hochwasserzentrale)
  * Alerts for breaking news from **Tagesschau** (via https://www.tagesschau.de)
  * Notification via **Email**
  * Notification via custom command, e.g. to create a Signal, Jabber, Matrix, SMS message
  * Regional events can be filtered by location (based on county), multiple locations can be configured
  * Automatic creation of a map image for each event if it contains geo coordinates
  * Event state is stored in a SQLite database to not create alerts for already alerted events
  * Made with Python and love


## Installation and setup

Ninette requires Python 3.8 or newer.
The easiest method is to install directly from pypi using pip:

    pip install ninette

When installing or running manually, the following requirements must be installed:
html2text, py-staticmaps, requests

Before using Ninette, you need to create a configuration file called `ninette.conf`.
Ninette will search for `ninette.conf` in the following locations (in that order):

  - /etc/ninette.conf
  - ~/.config/ninette.conf
  - ninette.conf (in current working directory)

Alternatively, you can specify the name of the configuration file to be read
using the `--config` command line parameter.

An example configuration file can be found in the sources or online
at https://raw.githubusercontent.com/eht16/ninette/main/ninette.conf.example.

For details on the configuration options, consider the comments in the
example configuration file.


## Usage

Run only once:

    ninette

Run in foreground:

    ninette -f

Run in foreground and override configured event fetch interval to 5 minutes (300 seconds):

    ninette -f -i 300

Run with verbose output and dry-run to *not* send any alerts:

    ninette -v -n


## Command line options

    usage: ninette [-h] [-V] [-d] [-v] [-c FILE] [-f] [-i NUM] [-n]

    options:
      -h, --help            show this help message and exit
      -V, --version         show version and exit (default: False)
      -d, --debug           enable tracebacks and enable --verbose (default: False)
      -v, --verbose         Show more log messages (default: False)
      -c FILE, --config FILE
                            configuration file path (default: None)
      -f, --foreground      Keep running in foreground (default: False)
      -i NUM, --interval NUM
                            Check for new events every X seconds (only used when in foreground) (default: None)
      -n, --dry-run         Dry run mode - do not send and remember any alerts (default: False)


## Available providers

**NINA provider** uses the NINA API (https://nina.api.bund.dev/) which is based on the warnings
of the German Bundesamt für Bevölkerungsschutz (https://warnung.bund.de).

In general the alerts are created if the configured area is affected by accidents or disasters
(fire, flood or a release of hazardous substances) from the following services:

- MoWaS (modular warning system)
- DWD - Deutscher Wetterdienst (weather service for Germany)
- Hochwasserzentrale (flood warnings for Germany)

The provider can generate alerts for multiple areas which are listed in the configuration file.
To add an area, the "[Amtlicher Gemeindeschlüssel](https://en.wikipedia.org/wiki/Community_Identification_Number#Germany)"
(Community Identification Number) for the area must be used.
A list of such numbers can be found on https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:rs.

Since the warnings are provided only on county level, the last seven digits of the number must be
replaced by "0000000".

**Tagesschau breaking news provider** queries the German television news service for breaking
news and creates alerts for each breaking news.

**Ping provider** a provider for debugging purposes only which generates an alert every hour.


## Available alerters

**Email alerter** sends an email to a configured list of recipients, email server
and credentials can be configured.

**Command alerter** executes a custom command which receives all alert information so it can generate
a push notification or SMS for a mobile phone, a message in a chat like Matrix, a message for a Pager
or any other form of notification or post processing.


## Disclaimer

Use this tool at your own risk only.
There is no warranty that all alerts are processed and sent reliably and in time.

This project has no relation to the official German NINA warn app.


## Author

Enrico Tröger <enrico.troeger@uvena.de>
