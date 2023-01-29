#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from configparser import ConfigParser
from importlib import import_module
import os

from ninette.configuration import Configuration


class NinetteConfigParser:

    def __init__(self, options):
        self._options = options
        self._config = None
        self._config_parser = None
        self._config_file_paths = None

    def parse(self):
        self._fetch_config_file_paths()
        self._init_config()
        self._read_config()
        self._parse_config()
        self._override_config_options_from_command_line()
        return self._config

    def _fetch_config_file_paths(self):
        self._config_file_paths = (
            '/etc/ninette.conf',
            os.path.expanduser('~/.config/ninette.conf'),
            'ninette.conf')

    def _init_config(self):
        self._config = Configuration()

    def _read_config(self):
        self._config_parser = ConfigParser()
        # read config file from location as specified via command line but fail it if doesn't exist
        if self._options.config_file_path:
            with open(self._options.config_file_path, encoding='utf-8') as config_file_h:
                self._config_parser.read_file(config_file_h)
                return
        # otherwise try pre-defined config file locations
        elif self._config_parser.read(self._config_file_paths):
            return
        # if we still didn't read any configuration file, bail out
        raise RuntimeError('No config file found')

    def _parse_config(self):
        for section_name in self._config_parser.sections():
            if section_name == 'general':
                self._parse_general_settings(section_name)
            elif section_name.startswith('provider_'):
                self._parse_module_settings(section_name, self._config.providers)
            elif section_name.startswith('alerter_'):
                self._parse_module_settings(section_name, self._config.alerters)

    def _parse_general_settings(self, section_name):
        parser = self._config_parser
        self._config.database_filename = parser.get(section_name, 'database_filename',
                                                    fallback='ninette.db')
        self._config.language_codes = parser.get(section_name, 'language_codes', fallback='en')
        self._config.timeout = parser.getfloat(section_name, 'timeout', fallback=60)
        self._config.log_format = parser.get(
            section_name, 'log_format', raw=True,
            fallback='%(asctime)s [%(levelname)+8s] [%(name)-24s] {dry_run}%(message)s')
        self._config.http_proxy = parser.get(section_name, 'http_proxy', fallback=None)
        self._config.http_useragent = parser.get(section_name, 'http_useragent', fallback=None)
        self._config.fetch_interval = parser.getint(section_name, 'fetch_interval', fallback=300)
        self._config.alerts_max_days = parser.getint(section_name, 'alerts_max_days', fallback=180)

        language_codes = self._config.language_codes.split(' ')
        self._config.language_codes = [code.lower().replace('-', '_') for code in language_codes]

    def _parse_module_settings(self, section_name, target):
        enabled = self._config_parser.getboolean(section_name, 'enable', fallback=False)
        if enabled:
            class_path = self._config_parser.get(section_name, 'class_path')
            provider = self._factor_class_from_path(class_path, section_name)
            target.append(provider)

    def _factor_class_from_path(self, class_path, section_name):
        module_name, class_name = class_path.rsplit('.', 1)
        module = import_module(module_name)
        class_ = getattr(module, class_name, None)
        return class_.create_from_config(self._config, self._config_parser, section_name)

    def _override_config_options_from_command_line(self):
        self._config.fetch_interval = self._options.fetch_interval or self._config.fetch_interval
        self._config.verbose = self._config.verbose or self._options.verbose or self._config.debug
        self._config.foreground = self._options.foreground or self._config.foreground
        self._config.debug = self._options.debug or self._config.debug
        self._config.dry_run = self._options.dry_run
