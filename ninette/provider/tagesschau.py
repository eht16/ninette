#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from ninette.provider.base import ProviderBase


ALERT_TEXT = '''Eilmeldung: {title}
Id:         {identifier}
Datum:      {date}
URL:        {url}


{text}


Mehr Informationen unter: {url}
'''


class TagesschauBreakingNewsProvider(ProviderBase):

    def __init__(self, config, class_path, fetch_interval, api_url):
        super().__init__(config, class_path, fetch_interval)
        self._api_url = api_url

    @classmethod
    def create_from_config(cls, config, config_parser, section_name):
        class_path = config_parser.get(section_name, 'class_path')
        fetch_interval = config_parser.getint(section_name, 'fetch_interval')
        api_url = config_parser.get(section_name, 'api_url')
        instance = cls(config, class_path, fetch_interval, api_url)
        return instance

    def _process(self):
        self._logger.info('Checking for Tagesschau breaking news')
        alerts = self._process_tagesschau_breaking_news()
        return alerts

    def _process_tagesschau_breaking_news(self):
        news = self._fetch_tagesschau_news_feed()
        alert = self._process_tagesschau_news(news)
        if alert:
            if self._alert_needs_to_be_processed(alert):
                self._mark_alert_as_processed(alert)
                return [alert]
            else:
                self._logger.debug('Skipping already processed alert "%s"', alert.identifier)

        return None

    def _fetch_tagesschau_news_feed(self):
        response = self._perform_http_request(self._api_url)
        return response.json()

    def _process_tagesschau_news(self, news):
        if 'breakingNews' in news:
            breaking_news = news['breakingNews']
            alert_text = ALERT_TEXT.format(
                identifier=breaking_news['id'],
                title=breaking_news['headline'],
                url=breaking_news['url'],
                text=breaking_news['text'],
                date=breaking_news['date'])

            alert = self._factor_alert(
                identifier=breaking_news['id'],
                title=f'Tagesschau: {breaking_news["headline"]}',
                alert_type='BreakingNews',
                text=alert_text)

            # attach the original json to the alert
            alert.attach_original_event(news)

            return alert

        return None
