#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import sys

from ninette.config import NinetteConfigParser
from ninette.main import NinetteRunner
from ninette.options import NinetteArgumentParser


def main():
    options = _setup_options()
    try:
        config = _setup_config(options)
        controller = NinetteRunner(config)
        if options.version:
            controller.show_version()
        else:
            controller.process()
    except Exception as exc:  # pylint: disable=broad-except
        if options.debug:
            raise

        print(exc)  # noqa: T201
        sys.exit(1)


def _setup_options():
    argument_parser = NinetteArgumentParser()
    return argument_parser.parse()


def _setup_config(options):
    config_parser = NinetteConfigParser(options)
    return config_parser.parse()


if __name__ == '__main__':
    main()
