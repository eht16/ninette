#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser


class NinetteArgumentParser:

    def __init__(self, argv=None):
        self._argv = argv
        self._argument_parser = None
        self._arguments = None

    def parse(self):
        self._init_argument_parser()
        self._setup_arguments()
        self._parse_arguments()
        return self._arguments

    def _init_argument_parser(self):
        self._argument_parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    def _setup_arguments(self):
        self._argument_parser.add_argument(
            '-V',
            '--version',
            dest='version',
            action='store_true',
            help='show version and exit',
            default=False)

        self._argument_parser.add_argument(
            '-d',
            '--debug',
            dest='debug',
            action='store_true',
            help='enable tracebacks and enable --verbose',
            default=False)

        self._argument_parser.add_argument(
            '-v',
            '--verbose',
            dest='verbose',
            action='store_true',
            help='Show more log messages',
            default=False)

        self._argument_parser.add_argument(
            '-c',
            '--config',
            dest='config_file_path',
            metavar='FILE',
            help='configuration file path')

        self._argument_parser.add_argument(
            '-f',
            '--foreground',
            dest='foreground',
            action='store_true',
            help='Keep running in foreground')

        self._argument_parser.add_argument(
            '-i',
            '--interval',
            dest='fetch_interval',
            metavar='NUM',
            type=int,
            help='Check for new events every X seconds (only used when in foreground)')

        self._argument_parser.add_argument(
            '-n',
            '--dry-run',
            dest='dry_run',
            action='store_true',
            help='Dry run mode - do not send and remember any alerts',
            default=False)

    def _parse_arguments(self):
        self._arguments = self._argument_parser.parse_args(self._argv)
