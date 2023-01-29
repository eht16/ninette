#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from abc import abstractmethod

from ninette.module import ModuleBase


class AlerterBase(ModuleBase):

    @abstractmethod
    def process(self, alerts):  # noqa
        raise NotImplementedError
