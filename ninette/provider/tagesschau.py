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
        alerts = self._process_tagesschau_news(news)
        for alert in list(alerts):
            if self._alert_needs_to_be_processed(alert):
                self._mark_alert_as_processed(alert)
            else:
                self._logger.debug('Skipping already processed alert "%s"', alert.identifier)
                alerts.remove(alert)

        return alerts or None

    def _fetch_tagesschau_news_feed(self):
        response = self._perform_http_request(self._api_url)
        return response.json()

    def _process_tagesschau_news(self, news):
        alerts_news = self._process_news_list(news.get('news', []))
        alerts_regional = self._process_news_list(news.get('regional', []))
        return alerts_news + alerts_regional

    def _process_news_list(self, news):
        alerts = []
        for news_item in news:
            if news_item['breakingNews']:
                text = self._factor_breaking_news_text(news_item)
                alert_text = ALERT_TEXT.format(
                    identifier=news_item['sophoraId'],
                    title=news_item['title'],
                    url=news_item['detailsweb'],
                    text=text,
                    date=news_item['date'])

                alert = self._factor_alert(
                    identifier=news_item['sophoraId'],
                    title=f'Tagesschau: {news_item["title"]}',
                    alert_type='BreakingNews',
                    text=alert_text)

                # attach the original json to the alert
                alert.attach_original_event(news_item)

                alerts.append(alert)

        return alerts

    def _factor_breaking_news_text(self, news_item):
        news_text = []
        for content_item in news_item.get('content', []):
            if content_item['type'] == 'text':
                plain_text = self._replace_html(content_item['value'])
                news_text.append(plain_text)
                news_text.append('\n')
            elif content_item['type'] == 'headline':
                news_text.append('\n')
                plain_text = self._replace_html(content_item['value'])
                news_text.append(plain_text)
                news_text.append('\n')

        return '\n'.join(news_text)
