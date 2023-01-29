#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.


class Module:

    def __init__(self):
        self.enabled = None
        self.class_path = None


class Configuration:  # pylint: disable=too-few-public-methods,too-many-instance-attributes

    def __init__(self):
        self.database_filename = None
        self.fetch_interval = None
        self.alerts_max_days = None
        self.http_proxy = None
        self.http_useragent = None
        self.timeout = None
        self.log_format = None
        self.language_codes = None
        self.timezone = None
        self.foreground = None
        self.verbose = None
        self.debug = None
        self.dry_run = None

        self.providers = []
        self.alerters = []

    def __repr__(self):
        return f'<{self.__class__.__name__}(debug={self.debug}, verbose={self.verbose})>'
