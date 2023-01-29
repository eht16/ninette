#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from contextlib import contextmanager
from datetime import datetime, timezone
import sqlite3


DATABASE_SCHEMA_STATEMENTS = [
    '''
    CREATE TABLE IF NOT EXISTS `alert` (
    `alert_id`          TEXT NOT NULL PRIMARY KEY,
    `alert_type`        TEXT NOT NULL,
    `provider`          TEXT NOT NULL,
    `entry_date`        DATETIME NOT NULL,
    `expire_date`       DATETIME);
    ''',
    'CREATE INDEX IF NOT EXISTS `idx_alert_type` ON `alert` (`alert_type`);',
    'CREATE INDEX IF NOT EXISTS `idx_alert_provider` ON `alert` (`provider`);',
    'CREATE INDEX IF NOT EXISTS `idx_entry_date` ON `alert` (`entry_date`);',
    'CREATE INDEX IF NOT EXISTS `idx_expire_date` ON `alert` (`expire_date`);',
    'CREATE UNIQUE INDEX IF NOT EXISTS `idx_alert` ON `alert` (`alert_id`, `alert_type`, `provider`);'  # noqa
]


class Database:

    def __init__(self, path):
        self._database_path = path
        self._connection = None

    def insert_alert(self, alert):
        query = '''
            INSERT INTO `alert` (`alert_id`, `alert_type`, `provider`, `entry_date`, `expire_date`)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT DO UPDATE SET `expire_date`=`excluded`.`expire_date`;'''

        # convert expire_date to UTC
        expire_date = alert.expire_date.astimezone(timezone.utc) if alert.expire_date else None

        with self._connect() as connection:
            connection.execute(query, (alert.identifier,
                                       alert.alert_type,
                                       alert.provider_name,
                                       datetime.now(timezone.utc),
                                       expire_date))

    def get_alert_expire_date(self, alert):
        # check if the alert was already processed but treat alerts with an expiry date as
        # unprocessed: update for alerts by "LHP" (flood reporting) are sent with the
        # same identifier and the type but their start and end dates will be updated
        query = '''SELECT `expire_date`
                   FROM `alert`
                   WHERE `alert_id`=? AND `alert_type`=? AND `provider`=?;'''
        with self._connect() as connection:
            cursor = connection.cursor()
            result = cursor.execute(
                query, (alert.identifier, alert.alert_type, alert.provider_name))
            if row := result.fetchone():
                return row['expire_date']

        return None

    def alert_exists(self, alert):
        query = '''SELECT 1
                   FROM `alert`
                   WHERE `alert_id`=? AND `alert_type`=? AND `provider`=?;
                '''
        with self._connect() as connection:
            cursor = connection.cursor()
            result = cursor.execute(
                query, (alert.identifier, alert.alert_type, alert.provider_name))
            if result.fetchone() is not None:
                return True

        return False

    def expire_alerts(self, provider, keep_alert_days=30):
        query = f'''DELETE FROM `alert`
                    WHERE `provider`= ?
                      AND (`expire_date` < datetime("now")
                            OR `entry_date` < datetime('now', "-{keep_alert_days} days"));'''
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(query, (provider,))
            return cursor.rowcount

    @contextmanager
    def _connect(self):
        self._open()
        try:
            with self._connection as connection:
                yield connection
        finally:
            self._close()

    def _open(self):
        self._connection = sqlite3.connect(
            self._database_path,
            timeout=30,
            isolation_level='EXCLUSIVE')
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self):
        cursor = self._connection.cursor()
        try:
            for statement in DATABASE_SCHEMA_STATEMENTS:
                cursor.execute(statement)
        except Exception:
            self._close()
            raise

    def _close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None
