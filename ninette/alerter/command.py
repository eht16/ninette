#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from tempfile import NamedTemporaryFile
import os
import subprocess

from ninette.alerter.base import AlerterBase


class CommandAlerterException(Exception):
    pass


class CommandAlerter(AlerterBase):

    def __init__(self, config, command, alert_text_via_stdin, attach_original_event):
        super().__init__(config)
        self.command = command
        self.alert_text_via_stdin = alert_text_via_stdin
        self.attach_original_event = attach_original_event

    @classmethod
    def create_from_config(cls, config, config_parser, section_name):
        command = config_parser.get(section_name, 'command')

        alert_text_via_stdin = config_parser.getboolean(
            section_name, 'alert_text_via_stdin', fallback=False)

        attach_original_event = config_parser.getboolean(
            section_name, 'attach_original_event', fallback=False)

        instance = cls(config, command, alert_text_via_stdin, attach_original_event)
        return instance

    def process(self, alerts):
        if not alerts:
            return

        for alert in alerts:
            try:
                self._process_alert(alert)
            except Exception as exc:
                self._logger.error('Error while executing command for alert "%s": %s',
                                   alert.identifier, exc)

    def _process_alert(self, alert):
        attachments_filenames = self._create_attachments_temporary_files(alert)
        try:
            # process placeholders
            command = self.command.format(
                alert_attachments=','.join(attachments_filenames) or 'None',
                alert_identifier=alert.identifier,
                alert_title=alert.title,
                alert_text=alert.text,
                alert_expire_date=alert.expire_date,
                alert_alert_type=alert.alert_type,
                alert_provider_name=alert.provider_name)

            if self.alert_text_via_stdin:
                alert_text_stdin = alert.text.encode('utf-8')
            else:
                alert_text_stdin = None

            output = self._execute_command(command, alert_text_stdin)

            command_for_log = f'{command[:60]}...'
            self._logger.info('Successfully executed command "%s" for alert "%s". Output: %s',
                              command_for_log, alert.identifier, output)
        finally:
            self._remove_temporary_files(attachments_filenames)

    def _create_attachments_temporary_files(self, alert):
        attachments_filenames = []
        for attachment_filename, attachment_content, _ in alert.attachments:
            # ignore the original event JSON if not enabled
            if not self.attach_original_event \
                    and alert.is_attachment_filename_original_event(attachment_filename):
                continue

            temp_file_suffix = f'ninette_{attachment_filename}'
            with NamedTemporaryFile(suffix=temp_file_suffix, delete=False) as temp_file:
                temp_file.write(attachment_content)

            attachments_filenames.append(temp_file.name)

        return attachments_filenames

    def _execute_command(self, command, alert_text_stdin):
        if self._config.dry_run:
            return 'dry-run activate, command was not executed.'

        try:
            output_bytes = subprocess.check_output(command, shell=True,  # noqa: SCS103
                                                   input=alert_text_stdin, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            output = self._process_command_output(exc.output)
            command_for_log = f'{command[:60]}...'
            exit_code = exc.returncode
            msg = f'Command "{command_for_log}" failed with exit code {exit_code}. Output: {output}'
            raise CommandAlerterException(msg) from exc

        return self._process_command_output(output_bytes)

    @staticmethod
    def _process_command_output(output_bytes):
        return output_bytes.decode('utf-8').strip()

    @staticmethod
    def _remove_temporary_files(filenames):
        if filenames is None:
            return

        for filename in filenames:
            try:
                os.unlink(filename)
            except FileNotFoundError:
                pass
