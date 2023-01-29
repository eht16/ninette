#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import json


class Alert:

    def __init__(self, provider_name, identifier, title, text=None,
                 alert_type=None, expire_date=None):
        self.provider_name = provider_name
        self.identifier = identifier
        self.alert_type = alert_type
        self.expire_date = expire_date
        self.title = title
        self.text = text
        self.attachments = []

    def attach_original_event(self, original_event):
        formatted_original_json = json.dumps(original_event, sort_keys=True, indent=2)
        formatted_original_json_bytes = formatted_original_json.encode('utf-8')
        filename = self._factor_original_event_filename()
        self.add_attachment(filename, formatted_original_json_bytes, 'text/plain')

    def add_attachment(self, filename, content, mimetype):
        self.attachments.append((filename, content, mimetype))

    def is_attachment_filename_original_event(self, filename):
        expected_filename = self._factor_original_event_filename()
        return filename == expected_filename

    def _factor_original_event_filename(self):
        return f'original_event_{self.identifier}.json'

    def __str__(self):
        return (f'{self.__class__.__name__}(identifier={self.identifier}, '
                f'provider_name={self.provider_name}, type={self.alert_type})')
