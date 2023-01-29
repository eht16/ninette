#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from abc import abstractmethod
import logging

import html2text


class ModuleBase:
    """ Base class for Providers and Alerters """

    def __init__(self, config):
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    @abstractmethod
    def create_from_config(cls, config, config_parser, section_name):
        raise NotImplementedError

    def _replace_html(self, html, bodywidth=72):
        text = html2text.html2text(html, bodywidth=bodywidth)
        text = text.replace('\\', '')  # remove escapes for list items, we don't need Markdown
        text = text.strip()
        return text
