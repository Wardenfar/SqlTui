from _ast import Not
from os import walk
from os.path import join

import toml
from pygments.lexers.sql import MySqlLexer, PostgresLexer


class Connection:

    def __init__(self, driver):
        self.driver = driver

    def lexer(self):
        return None

    def name(self):
        raise NotImplemented("name not implemented")

    def connect(self):
        raise NotImplemented('connect not implemented')

    def execute(self, query):
        raise NotImplemented("execute not implemented")

    def close(self):
        raise NotImplemented("close not implemented")

    def escape(self, type, value):
        raise NotImplemented("escape not implemented")


class Driver:

    def __init__(self, data, nodes):
        self.data = data
        self.nodes = nodes

        self.root = data['root']
        self.name = data['full_name']

    def open_connection(self, type, parents):
        raise NotImplemented("open_connection not implemented")


class PsqlConnection(Connection):

    def __init__(self, dsn):
        dsn = dsn.copy()
        del dsn['driver']
        self.dsn = dsn
        self.conn = None
        self.connect()

    def __str__(self):
        name = 'Database <' + self.dsn['database'] + '>' if 'database' in self.dsn else 'Server'
        return 'Psql {} {}:{}'.format(name, self.dsn['host'], self.dsn['port'])

    def name(self):
        return self.dsn['host'] + ':' + self.dsn['port']

    def lexer(self):
        return PostgresLexer

    def connect(self):
        import psycopg2
        self.conn = psycopg2.connect(**self.dsn)

    def execute(self, query, reconnect=False):
        conn = self.conn
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)

                result = []
                columns = []

                try:
                    result = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                except:
                    pass

                conn.commit()

                return result, columns
        except Exception as e:
            if reconnect and (not conn.isolation_level or conn.isolation_level > 0):
                conn.rollback()

            if 'cannot run inside a transaction block' in str(e):
                if not conn.isolation_level or conn.isolation_level > 0:
                    conn.set_isolation_level(0)
                    final = self.execute(query)
                    conn.set_isolation_level(1)
                    return final
            elif not reconnect:
                try:
                    self.connect()
                    return self.execute(query, True)
                except Exception as e2:
                    raise e
            else:
                raise e

    def close(self):
        self.conn.close()

    def escape(self, type, value):
        from psycopg2 import sql
        if not type:
            return value
        elif type == 'id':
            return sql.Identifier(*value.split('.')).as_string(self.conn)
        elif type == 'text':
            return sql.Literal(value).as_string(self.conn)
        elif type == 'number':
            return sql.Literal(float(value)).as_string(self.conn)


class PsqlDriver(Driver):

    def open_connection(self, conn_type, parents):
        root = parents['server'].data
        if conn_type == 'server':
            return PsqlConnection(root.dsn)

        if conn_type == 'database':
            new_dsn = root.dsn.copy()
            new_dsn['database'] = parents['database'].data[0]
            return PsqlConnection(new_dsn)


class MySqlConnection(Connection):

    def __init__(self, dsn):
        dsn = dsn.copy()
        del dsn['driver']
        self.dsn = dsn
        self.conn = None
        self.connect()

    def __str__(self):
        name = 'Database <' + self.dsn['database'] + '>' if 'database' in self.dsn else 'Server'
        return 'MySql {} {}:{}'.format(name, self.dsn['host'], self.dsn['port'])

    def lexer(self):
        return MySqlLexer

    def connect(self):
        import mysql.connector
        self.conn = mysql.connector.connect(**self.dsn)

    def name(self):
        return self.dsn['host'] + ':' + self.dsn['port']

    def execute(self, query, reconnect=False):
        conn = self.conn
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)

                result = []
                columns = []

                try:
                    result = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                except:
                    pass

                conn.commit()

                return result, columns
        except Exception as e:
            if not reconnect:
                try:
                    self.connect()
                    self.execute(query, True)
                except Exception as e2:
                    raise e
            else:
                raise e

    def close(self):
        self.conn.close()

    def escape(self, type, value):
        if not type:
            return value
        elif type == 'id':
            return '`' + value.replace('`', '\\`') + '`'
        elif type == 'text':
            return '"' + value.replace('"', '\\"') + '"'
        elif type == 'number':
            return value


class MySqlDriver(Driver):

    def open_connection(self, conn_type, parents):
        root = parents['server'].data
        if conn_type == 'server':
            return MySqlConnection(root.dsn)

        if conn_type == 'database':
            new_dsn = root.dsn.copy()
            new_dsn['database'] = parents['database'].data[0]
            return MySqlConnection(new_dsn)


DRIVERS_CLASSES = {
    'psql': PsqlDriver,
    'mysql': MySqlDriver
}

_, _, filenames = next(walk('config/drivers'))

filenames = list(map(lambda p: join('config/drivers', p), filenames))

DRIVERS = {}

for file in filenames:
    data = toml.load(file)

    for key in data['driver']:
        driver_data = data['driver'][key]
        driver_nodes = data[key]['node']
        DRIVERS[key] = DRIVERS_CLASSES[key](driver_data, driver_nodes)
