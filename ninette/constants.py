#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import sys
from pathlib import Path

from ninette import __version__ as VERSION  # noqa: N812


PROGRAM_NAME = Path(sys.argv[0]).name
APP_NAME_VERSION = f'Ninette {VERSION}'
