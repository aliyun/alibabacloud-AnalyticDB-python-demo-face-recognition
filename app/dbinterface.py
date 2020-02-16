# Copyright @ 2020 Alibaba. All rights reserved.
import psycopg2
import time
import sys
class DBInterface:
    def __init__(self, host="127.0.0.1", port="5432", database="postgres", user="postgres", password=""):
        pass

    def make_connection(self):
        pass

    def commit(self):
        pass

    def sql_worker(self, sql, not_fetch_result, is_print):
        pass

    def close(self):
        pass


class DBInterfacePG(DBInterface):
    def __init__(self, host="127.0.0.1", port="5432", database="postgres", user="postgres", password=""):
        DBInterface.__init__(self)
        self.lines = []
        self.conn, self.cursor = None, None
        self.host, self.port, self.database, self.user, self.password = host, port, database, user, password
        self.make_connection()

    def make_connection(self):
        self.conn = psycopg2.connect(database=self.database, user=self.user, password=self.password, host=self.host,
                                     port=self.port)
        self.cursor = self.conn.cursor()
        self.conn.autocommit = True

    def commit(self):
        self.conn.commit()

    def sql_worker(self, sql, not_fetch_result, is_print):
        rows = []
        time1 = time.time()
        self.make_connection()
        self.cursor.execute(sql)
        # self.cursor.close()
        if not not_fetch_result:
            try:
                rows = self.cursor.fetchall()
            except psycopg2.ProgrammingError as e:
                print e.message, type(e)
                rows = "Done"
        time2 = time.time()
        rt = time2 - time1
        if is_print:
            print "rt=" + str(rt)
            sys.stdout.flush()
        return rows, rt

    def close(self):
        self.cursor.close()
        self.conn.close()