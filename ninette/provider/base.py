#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from abc import abstractmethod
from datetime import datetime, timedelta, timezone

import requests

from ninette.alert import Alert
from ninette.module import ModuleBase


class ProviderBase(ModuleBase):

    def __init__(self, config, class_path, fetch_interval):
        super().__init__(config)
        self._database = None
        self._class_path = class_path
        self._fetch_interval = fetch_interval
        self._last_runtime = None

    def set_database(self, database):
        self._database = database

    def should_run(self):
        if not self._last_runtime:
            return True

        now = datetime.now(timezone.utc)
        if now >= (self._last_runtime + timedelta(seconds=self._fetch_interval)):
            return True

        return False

    def run(self):
        self._last_runtime = datetime.now(timezone.utc)
        try:
            alerts = self._process()
        except Exception as exc:
            self._logger.error('Error while fetching new alerts: %s', exc,
                               exc_info=self._config.debug)
            return None

        self._expire_alerts()
        return alerts

    @abstractmethod
    def _process(self):
        raise NotImplementedError

    def _alert_needs_to_be_processed(self, alert):
        if alert and self._config.dry_run:
            self._logger.debug('Alert "%s" would need processing', alert)
            return True  # always process events in dry-run mode

        if alert:
            return not self._database.alert_exists(alert)

        return False

    def _expire_alerts(self):
        deleted_row_count = self._database.expire_alerts(self._class_path,
                                                         self._config.alerts_max_days)
        self._logger.debug('Expired %s "%s" alerts (max age %s days)',
                           deleted_row_count, self.__class__.__name__, self._config.alerts_max_days)

    def _mark_alert_as_processed(self, alert):
        if self._config.dry_run:
            self._logger.debug('Alert "%s" would be marked as processed', alert)
            return  # do *not* write to database in dry-run mode

        if alert:
            self._database.insert_alert(alert)
            self._log_new_alert(alert)

    def _log_new_alert(self, alert):
        self._logger.info('Created new alert "%s"', alert.identifier)

    def _factor_alert(self, identifier, title, alert_type, text=None, expire_date=None):
        return Alert(
            provider_name=self._class_path,
            identifier=identifier,
            title=title,
            alert_type=alert_type,
            expire_date=expire_date,
            text=text)

    def _perform_http_request(self, url):
        response = requests.get(
            url,
            headers={'user-agent': self._config.http_useragent},
            proxies={'http': self._config.http_proxy, 'https': self._config.http_proxy},
            timeout=self._config.timeout
        )
        response.raise_for_status()
        return response
