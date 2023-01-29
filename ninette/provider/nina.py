#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from datetime import datetime, timezone
from io import BytesIO

import staticmaps

from ninette.provider.base import ProviderBase


class SkipAlreadyProcessedAlert(Exception):
    pass


class SkipFutureAlert(Exception):
    pass


class SkipPastAlert(Exception):
    pass


class NinaProvider(ProviderBase):
    """
    https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.html
    """

    NINA_URL_DASHBOARD = '{api_url}/dashboard/{ags}.json'
    NINA_URL_ALERT_DETAILS = '{api_url}/warnings/{identifier}.json'
    NINA_URL_ALERT_GEOJSON = '{api_url}/warnings/{identifier}.geojson'
    CAP_TEST_ALERT_STATES = ('Test', 'Draft', 'Exercise')
    DATETIME_FORMAT = '%A, %d.%m.%Y %H:%M'
    STATICMAP_WIDTH = 600
    STATICMAP_HEIGHT = 550
    ALERT_TEXT = '''NINA Warnmeldung: {title}

Id:             {identifier}
Datum:          {date}
URL:            {url}
Landkreis:      {county}
Kategorien:     {categories}
Event:          {event}
Dringlichkeit:  {urgency}
Schweregrad:    {severity}
Start:          {start_date}
Ende:           {end_date}
Sender:         {sender_name}
Regionen:       {areas}


{text}


Handlungsempfehlung:
{instruction}

Weitere Informationen:
{contact}


Mehr Informationen unter: {url}
'''

    def __init__(self, config, class_path, fetch_interval, base_url, enable_test_alerts, locations):
        super().__init__(config, class_path, fetch_interval)
        self._base_url = base_url
        self._enable_test_alerts = enable_test_alerts
        self._locations = locations
        self._alerts = None
        self._location_title = None

    @classmethod
    def create_from_config(cls, config, config_parser, section_name):
        class_path = config_parser.get(section_name, 'class_path')
        fetch_interval = config_parser.getint(section_name, 'fetch_interval')
        base_url = config_parser.get(section_name, 'base_url')
        enable_test_alerts = config_parser.getboolean(section_name, 'enable_test_alerts')
        locations = {}
        for name, value in config_parser.items(section_name):
            if name.startswith('ags_'):
                locations[name[4:]] = value

        instance = cls(config, class_path, fetch_interval, base_url, enable_test_alerts, locations)
        return instance

    def _process(self):
        self._alerts = []
        for location_name, location_ags in self._locations.items():
            self._location_title = location_name.title()
            self._logger.debug('Checking for new Nina alerts in AGS "%s"', self._location_title)
            try:
                self._process_nina_alerts(location_ags)
            except Exception as exc:
                self._logger.error('Error while processing alerts for AGS "%s": %s',
                                   self._location_title, exc)

        return self._alerts

    def _process_nina_alerts(self, location_ags):
        messages = self._fetch_nina_alerts(location_ags)
        for message in messages:
            try:
                alert = self._process_nina_message(message)
                if self._alert_needs_to_be_processed(alert):
                    self._fetch_alert_details(alert)
                    self._alerts.append(alert)
                    self._mark_alert_as_processed(alert)
                else:
                    raise SkipAlreadyProcessedAlert()
            except SkipFutureAlert:
                self._logger.debug('Skipping not yet effective alert "%s"', alert.identifier)
            except SkipPastAlert:
                self._logger.debug('Skipping past alert "%s"', alert.identifier)
            except SkipAlreadyProcessedAlert:
                self._logger.debug('Skipping already processed alert "%s"', alert.identifier)
            except Exception as exc:
                self._logger.error('Error while processing alert "%s": %s', message['id'], exc)

    def _fetch_nina_alerts(self, location_ags):
        api_url = self.NINA_URL_DASHBOARD.format(api_url=self._base_url, ags=location_ags)
        response = self._perform_http_request(api_url)
        return response.json()

    def _process_nina_message(self, message):
        # ignore this alert unless processing test alerts is requested
        status = self._get_nested_field_from_message(message, 'payload', 'data', 'status')
        if status in self.CAP_TEST_ALERT_STATES and not self._enable_test_alerts:
            return None

        identifier = message['id']
        alert_type = self._get_nested_field_from_message(message, 'payload', 'data', 'msgType')

        alert = self._factor_alert(identifier=identifier, alert_type=alert_type, title='')
        return alert

    @staticmethod
    def _get_nested_field_from_message(message, *field_path, fallback=None):
        element = message
        for key in field_path:
            try:
                element = element[key]
            except KeyError:
                return fallback

        return element

    def _alert_needs_to_be_processed(self, alert):
        alert_needs_to_be_processed = super()._alert_needs_to_be_processed(alert)

        # NINA / Mowas specific handling of expiry date on recurring event IDs (e.g. for LHP)
        if alert:
            if self._config.dry_run:
                return True  # always process events in dry-run mode

            if alert_needs_to_be_processed:
                return True  # process alerts which are not present in the database
            else:
                # if we got an alert, query its expire date, convert to datetime and set on alert
                expire_date = self._database.get_alert_expire_date(alert)
                if expire_date:
                    alert.expire_date = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S%z')
                # re-process existing alerts with an expire date set
                # ignore alerts present in the database without an expire_date
                return alert.expire_date is not None

        return False

    def _fetch_alert_details(self, alert):  # pylint: disable=too-many-locals,too-many-statements
        # fetch alert details
        api_url = self.NINA_URL_ALERT_DETAILS.format(api_url=self._base_url,
                                                     identifier=alert.identifier)
        response = self._perform_http_request(api_url)
        detail_message = response.json()

        # find the info block with the best matching language
        detail_info = None
        if len(detail_message['info']) > 1:
            for detail_info_tmp in detail_message['info']:
                language_code = detail_info_tmp.get('language', '').lower().replace('-', '_')
                if language_code in self._config.language_codes:
                    detail_info = detail_info_tmp
                    break

        if not detail_info:
            detail_info = detail_message['info'][0]  # fallback to the first item

        effective = self._parse_date(detail_info.get('effective'))
        expires = self._parse_date(detail_info.get('expires'))
        now = datetime.now(timezone.utc)

        # skip the alert for now, re-process it once it is effective
        if effective and effective > now:
            raise SkipFutureAlert()
        # skip past alerts
        if expires and expires <= now:
            raise SkipPastAlert()
        # skip processed alerts with an expire_date set
        if expires and alert.expire_date:
            raise SkipAlreadyProcessedAlert()

        date = self._parse_date(detail_message['sent'])
        headline = detail_info.get('headline', '')
        category_list = detail_info.get('category', [])
        area_list = detail_info.get('area', [])
        event = detail_info.get('event')
        urgency = detail_info.get('urgency')
        severity = detail_info.get('severity')
        headline = detail_info.get('headline')
        description = detail_info.get('description')
        instruction = detail_info.get('instruction', '')
        contact = detail_info.get('contact', '')
        url = detail_info.get('web', '')

        parameters = detail_info.get('parameter', [])
        sender_name = self._get_info_parameter(parameters, 'sender_langname', fallback='')
        instruction_text = self._get_info_parameter(parameters, 'instructionText', fallback='')

        # pre-process data as necessary
        categories = ', '.join(category_list)
        areas = ', '.join([area['areaDesc'] for area in area_list])

        # reformat timestamp
        date = self._format_date(date)
        start_date = self._format_date(effective)
        end_date = self._format_date(expires)
        # replace HTML in texts
        title = self._replace_html(headline, bodywidth=2000)
        text = self._replace_html(description)
        instruction = self._replace_html(instruction)
        contact = self._replace_html(contact)
        url = self._replace_html(url)

        instruction = self._factor_instruction_text(instruction, instruction_text)

        alert.expire_date = expires
        alert.title = f'NINA: {title} ({self._location_title})'
        alert.text = self.ALERT_TEXT.format(
            title=alert.title,
            categories=categories,
            identifier=alert.identifier,
            county=self._location_title,
            date=date,
            areas=areas,
            event=event,
            urgency=urgency,
            severity=severity,
            sender_name=sender_name,
            instruction=instruction,
            start_date=start_date,
            end_date=end_date,
            contact=contact,
            url=url,
            text=text,
        )
        # generate and attach a staticmap of the alert
        staticmap_image = self._create_staticmap_image(alert)
        staticmap_image_filename = f'staticmap_image_{alert.identifier}.png'
        alert.add_attachment(staticmap_image_filename, staticmap_image, 'image/png')
        # attach the original json to the alert
        alert.attach_original_event(detail_message)

    @staticmethod
    def _get_info_parameter(parameters, key, fallback=None):
        for parameter in parameters:
            if parameter['valueName'] == key:
                return parameter['value']

        return fallback

    def _format_date(self, date_unformatted):
        if date_unformatted is None:
            return ''

        if isinstance(date_unformatted, str):
            try:
                timestamp = self._parse_date(date_unformatted)
            except ValueError as exc:
                self._logger.info('Unable to format date "%s": %s', date_unformatted, exc)
                return date_unformatted
        else:
            timestamp = date_unformatted

        return timestamp.strftime(self.DATETIME_FORMAT)

    @staticmethod
    def _parse_date(date_string):
        if not date_string:
            return None

        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S%z')

    @staticmethod
    def _factor_instruction_text(instruction, instruction_text):
        if instruction_text:
            if instruction:
                instruction = f'{instruction}\n\n{instruction_text}'
            else:
                instruction = instruction_text

        return instruction

    def _create_staticmap_image(self, alert):
        response_geojson = self._get_geojson_from_api(alert)

        tile_downloader = staticmaps.TileDownloader()
        tile_downloader.set_user_agent(self._config.http_useragent)

        context = staticmaps.Context()
        context.set_tile_downloader(tile_downloader)
        context.set_tile_provider(staticmaps.tile_provider_OSM)

        self._add_polygons_to_content(response_geojson, context)

        image_buffer = BytesIO()
        image = context.render_pillow(self.STATICMAP_WIDTH, self.STATICMAP_HEIGHT)
        image.save(image_buffer, 'png')

        image_buffer.seek(0)
        image_bytes = image_buffer.getvalue()
        image_buffer.close()
        return image_bytes

    def _get_geojson_from_api(self, alert):
        api_url = self.NINA_URL_ALERT_GEOJSON.format(api_url=self._base_url,
                                                     identifier=alert.identifier)
        response = self._perform_http_request(api_url)
        return response.json()

    @staticmethod
    def _add_polygons_to_content(geojson, context):
        polygons = []
        for feature in geojson['features']:
            for coordinates in feature['geometry']['coordinates']:
                if feature['geometry']['type'] == 'MultiPolygon':
                    polygons.extend(coordinates)
                else:
                    polygons.append(coordinates)

        for polygon in polygons:
            latlngs = [staticmaps.create_latlng(lat, lng) for lng, lat in polygon]
            area = staticmaps.Area(latlngs, width=2,
                                   fill_color=staticmaps.parse_color('#00FF002F'),
                                   color=staticmaps.parse_color('#8888FF'))
            context.add_object(area)
