# -*- coding: utf-8 -*-
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import os
import sys

from ninette import __version__ as VERSION  # noqa


PROGRAM_NAME = os.path.basename(sys.argv[0])
APP_NAME_VERSION = f'Ninette {VERSION}'
