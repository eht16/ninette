#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from email.message import EmailMessage
from email.utils import formatdate
import smtplib

from ninette.alerter.base import AlerterBase
from ninette.constants import APP_NAME_VERSION


class EmailAlerterSMTPException(Exception):
    pass


class EmailAlerter(AlerterBase):

    # pylint:disable=too-many-arguments
    def __init__(self, config, recipients, from_address, smtp_server, smtp_port,
                 smtp_username, smtp_password, smtp_use_tls, attach_original_event):
        super().__init__(config)
        self.from_address = from_address
        self.recipients = recipients.split(',')
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls
        self.attach_original_event = attach_original_event

    @classmethod
    def create_from_config(cls, config, config_parser, section_name):
        recipients = config_parser.get(section_name, 'recipients')
        from_address = config_parser.get(section_name, 'from_address')
        smtp_server = config_parser.get(section_name, 'smtp_server')
        smtp_port = config_parser.getint(section_name, 'smtp_port')
        smtp_username = config_parser.get(section_name, 'smtp_username', fallback=None)
        smtp_password = config_parser.get(section_name, 'smtp_password', fallback=None)
        smtp_use_tls = config_parser.getboolean(section_name, 'smtp_use_tls', fallback=True)
        attach_original_event = config_parser.getboolean(
            section_name, 'attach_original_event', fallback=True)
        instance = cls(config, recipients, from_address, smtp_server, smtp_port,
                       smtp_username, smtp_password, smtp_use_tls, attach_original_event)
        return instance

    def process(self, alerts):
        if not alerts:
            return

        for alert in alerts:
            try:
                self._process_alert(alert)
            except Exception as exc:
                self._logger.error('Error while sending emails for alert "%s": %s',
                                   alert.identifier, exc)

    def _process_alert(self, alert):
        email_message = EmailMessage()
        email_message.set_content(alert.text)
        email_message['Subject'] = f'[Ninette] {alert.title}'
        email_message['From'] = self.from_address
        email_message['Date'] = formatdate(localtime=True)
        email_message['To'] = ''  # will be set below
        email_message['X-Mailer'] = APP_NAME_VERSION

        for filename, content, mimetype in alert.attachments:
            # ignore the original event JSON if not enabled
            if not self.attach_original_event \
                    and alert.is_attachment_filename_original_event(filename):
                continue

            mimetype_main, mimetype_sub = mimetype.split('/', 1)
            email_message.add_attachment(content, maintype=mimetype_main, subtype=mimetype_sub,
                                         filename=filename)

        for recipient in self.recipients:
            self._logger.info('Sending alert "%s" mail to "%s"', alert.identifier, recipient)
            email_message.replace_header('To', recipient)
            self._send_mail(recipient, email_message)

    def _send_mail(self, recipient, email_message):
        if self._config.dry_run:
            return

        try:
            smtp_class = smtplib.SMTP_SSL if self.smtp_use_tls else smtplib.SMTP
            connection = smtp_class(self.smtp_server, self.smtp_port)
            connection.ehlo()
            if connection.has_extn('STARTTLS'):
                connection.starttls()
            if self.smtp_username and self.smtp_password:
                connection.login(self.smtp_username, self.smtp_password)

            response = connection.send_message(email_message, self.from_address, [recipient])
            if response:
                for failed_recipient, error in response.items():
                    raise EmailAlerterSMTPException(
                        f'Unable to send email to "{failed_recipient}": {error}')
            connection.quit()
        except OSError as exc:
            raise EmailAlerterSMTPException(
                f'Unable to send email to "{recipient}": {exc}') from exc
