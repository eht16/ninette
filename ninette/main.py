#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from time import sleep
from traceback import format_exc
import logging
import os

from ninette.constants import APP_NAME_VERSION
from ninette.database import Database


class StopFetchLoop(Exception):
    pass


class NinetteRunner:

    def __init__(self, config):
        self._config = config
        self._database = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def show_version(self):
        print(APP_NAME_VERSION)  # noqa: T201

    def process(self):
        self._setup_http_proxy()
        self._setup_logging()
        self._setup_database()
        self._logger.debug('Starting %s', APP_NAME_VERSION)
        while True:
            try:
                self._fetch_alerts()
                self._wait_for_next_refresh_interval()
            except (StopFetchLoop, KeyboardInterrupt):
                break
            except Exception as exc:  # pylint: disable=broad-except
                if self._config.debug:
                    traceback = format_exc()
                    traceback = f'\n{traceback}'
                else:
                    traceback = ''
                self._logger.error('Unexpected error occurred: %s%s', exc, traceback)
                self._wait_for_next_refresh_interval()

        self._logger.debug('Stopping %s', APP_NAME_VERSION)

    def _setup_http_proxy(self):
        """
        If a HTTP proxy is configured, set it also as environment variable so also the "staticmaps"
        package will use it for map downloads.
        """
        if self._config.http_proxy:
            os.environ['http_proxy'] = self._config.http_proxy
            os.environ['https_proxy'] = self._config.http_proxy

    def _setup_logging(self):
        if self._config.debug or self._config.dry_run:
            level = logging.DEBUG
        elif self._config.verbose:
            level = logging.INFO
        else:
            level = logging.WARNING

        dry_run = 'DRY RUN: ' if self._config.dry_run else ''

        log_format = self._config.log_format.format(dry_run=dry_run)
        logging.basicConfig(level=level, format=log_format)

        # set log level for the PIL library to at least INFO
        pil_level = level if level >= logging.INFO else logging.INFO
        logging.getLogger('PIL').setLevel(pil_level)

    def _setup_database(self):
        self._database = Database(self._config.database_filename)
        for provider in self._config.providers:
            provider.set_database(self._database)

    def _fetch_alerts(self):
        self._logger.info('Checking for new alerts')

        for provider in self._config.providers:
            alerts = self._run_provider(provider)
            self._process_alerts(alerts)

    def _run_provider(self, provider):
        if provider.should_run():
            alerts = provider.run()
            return alerts

        return None

    def _process_alerts(self, alerts):
        if not alerts or not self._config.alerters:
            return

        for alerter in self._config.alerters:
            alerter.process(alerts)

    def _wait_for_next_refresh_interval(self):
        if not self._config.foreground:
            # raise a dedicated exception to break the while(true) loop in self.process()
            raise StopFetchLoop()

        self._logger.debug('Sleeping for %s seconds', self._config.fetch_interval)
        sleep(self._config.fetch_interval)
