#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from datetime import datetime, timezone

from ninette.provider.base import ProviderBase


class PingProvider(ProviderBase):

    @classmethod
    def create_from_config(cls, config, config_parser, section_name):
        class_path = config_parser.get(section_name, 'class_path')
        fetch_interval = config_parser.getint(section_name, 'fetch_interval', fallback=1800)
        return cls(config, class_path, fetch_interval)

    def _process(self):
        self._logger.info('Checking for new Ping alerts')
        alerts = []
        identifier = f'ping-{datetime.now(timezone.utc).strftime("%y-%m-%dT%H")}'
        text = 'Test alarm for debugging purposes\n\nThis event will be triggered every hour.\n'
        alert = self._factor_alert(identifier=identifier, title=f'TEST ALARM: {identifier}',
                                   alert_type='Ping', text=text)

        if self._alert_needs_to_be_processed(alert):
            self._logger.debug('New Ping alert: %s', alert.identifier)
            alerts.append(alert)
            self._mark_alert_as_processed(alert)

        return alerts
