# Copyright @ 2020 Alibaba. All rights reserved.
from dbinterface import DBInterfacePG
from datetime import datetime
import numpy as np
np.set_printoptions(threshold=np.inf)

class face_database:
    def __init__(self, host="127.0.0.1", port="5432", database="postgres", user="postgres", password="",
                 feature_length=1024, app_name="test", distance_measure="dot_product"):
        self.db = DBInterfacePG(host=host, port=port, database=database, user=user, password=password)
        self.db.make_connection()
        self.tb_name = "face_feature"
        self.tb_name_person = "person"
        self.tb_name_access = "access_record"
        self.tb_name_user = "user_account"
        self.feature_length = feature_length
        self.distance_measure = distance_measure
        self.user_name = None
        if distance_measure=="squared_l2":
            self.distance_udf = "l2_distance"
        elif distance_measure=="dot_product":
            self.distance_udf = "dp_distance"
        else:
            raise("distance measure %s is invalid"%distance_measure)

    def register(self, schema, feature, pid, name, gender=None, age=None, address=None):
        feature_str = np.array2string(feature, separator=',', max_line_width=np.inf)
        if name is None:
            return False

        if pid is None:
            sql = "select nextval('%s.seq_psid')" %schema
            pid = self.db.sql_worker(sql, not_fetch_result=False, is_print=False)[0][0][0]
        pid = int(pid)
        sql = "insert into %s.%s values ( default , %d, array%s::real[], null)" % (schema, self.tb_name, pid, feature_str)
        self.db.sql_worker(sql, not_fetch_result=True, is_print=False)
        if not gender:
            gender = "null"
        else:
            gender = "'%s'"%gender
        if not age:
            age = "null"
        if not address:
            address = "null"
        else:
            address = "'%s'"%address
        name = "'%s'" % name
        sql = "insert into %s.%s values(%d, %s, %s, %s, %s) ON conflict DO nothing;"%(schema, self.tb_name_person, pid, name, gender, age, address)
        self.db.sql_worker(sql, not_fetch_result=True, is_print=False)
        return True

    def register_mask(self, schema, feature, feature_partial, pid, name, gender=None, age=None, address=None):
        feature_str = np.array2string(feature, separator=',', max_line_width=np.inf)
        feature_partial_str = np.array2string(feature_partial, separator=',', max_line_width=np.inf)
        if name is None:
            return False

        if pid is None:
            sql = "select nextval('%s.seq_psid')" %schema
            pid = self.db.sql_worker(sql, not_fetch_result=False, is_print=False)[0][0][0]
        pid = int(pid)
        sql = "insert into %s.%s values ( default , %d, array%s::real[], array%s::real[])" \
              % (schema, self.tb_name, pid, feature_str, feature_partial_str)
        self.db.sql_worker(sql, not_fetch_result=True, is_print=False)
        if not gender:
            gender = "null"
        else:
            gender = "'%s'"%gender
        if not age:
            age = "null"
        if not address:
            address = "null"
        else:
            address = "'%s'"%address
        name = "'%s'" % name
        sql = "insert into %s.%s values(%d, %s, %s, %s, %s) ON conflict DO nothing;"%(schema, self.tb_name_person, pid, name, gender, age, address)
        self.db.sql_worker(sql, not_fetch_result=True, is_print=False)
        return True

    def get_num_records(self, schema):
        sql = "select count(*) from %s.%s"%(schema, self.tb_name)
        rows, _ = self.db.sql_worker(sql, not_fetch_result=False, is_print=False)
        return rows[0][0]

    def get_num_identity(self, schema):
        sql = "select count(*) from %s.%s"%(schema, self.tb_name_person)
        rows, _ = self.db.sql_worker(sql, not_fetch_result=False, is_print=False)
        return rows[0][0]

    def query(self, schema, feature, has_mask=False):
        return self.query_top_n(schema, feature, 1, has_mask)

    def query_top_n(self, schema, feature, top_n, has_mask=False):
        # set top N parameter for index
        sql = "Set fastann.topk=%d"%top_n
        self.db.sql_worker(sql, not_fetch_result=True, is_print=False)
        feature_str = np.array2string(feature, separator=',', max_line_width=np.inf)
        desc = "desc" if self.distance_measure == "dot_product" else ""
        # sql = "select pid, name, %s(feature, array%s::real[]) as distance from %s order by distance %s limit %d" \
        #       %(self.distance_udf, feature_str, self.tb_name, desc,top_n)
        if has_mask:
            feature_col = 'feature_partial'
        else:
            feature_col = 'feature'
        sql = """
            select A.pid, B.name, B.gender, B.age, %s(A.%s, array%s::real[]) as distance
            from %s.%s as A inner join %s.%s as B on A.pid = B.pid 
            order by distance %s limit %d
        """ %(self.distance_udf, feature_col, feature_str, schema, self.tb_name, schema, self.tb_name_person, desc, top_n)
        rows, _ = self.db.sql_worker(sql, not_fetch_result=False, is_print=False)
        return rows
    
    def query_top_n_above(self, schema, feature, top_n, thre, has_mask=False):
        rows = self.query_top_n(schema, feature, top_n, has_mask)
        if self.distance_measure=="squared_l2":
            rows = [row for row in rows if row[-1] < thre]
        elif self.distance_measure=="dot_product":
            rows = [row for row in rows if row[-1] > thre]
        else:
            raise ("distance measure %s is not defined" % self.distance_measure)
        return rows

    def create_table(self, schema=None):
        if schema is not None:
            # create a table for features
            sql = "create sequence if not exists %s.seq_pid as bigint" %schema
            self.db.sql_worker(sql, True, False)
            sql = """create table if not exists %s.%s (
                        id bigint default nextval('%s.seq_pid') primary key,
                        pid bigint,
                        feature real[%d],
                        feature_partial real[%d]
                    )""" \
                    %(schema,  self.tb_name, schema,  self.feature_length,  self.feature_length)
            self.db.sql_worker(sql, True, False)
            sql = "create index if not exists %s_idx on %s.%s using ann(feature) with(distancemeasure=L2,dim=%d,pq_segments=128)"\
                  %(self.tb_name, schema, self.tb_name, self.feature_length)
            self.db.sql_worker(sql, True, False)

            # create table for visiting records
            sql = "create sequence if not exists %s.seq_id as bigint" %schema
            self.db.sql_worker(sql, True, False)
            sql = """create table if not exists %s.%s (
                        id bigint default nextval('%s.seq_id') primary key,
                        pid bigint,
                        time timestamp
                    )""" \
                    %(schema, self.tb_name_access, schema)
            self.db.sql_worker(sql, True, False)

            sql = "create sequence if not exists %s.seq_psid as bigint" %schema
            self.db.sql_worker(sql, True, False)
            # create table for person information
            sql = """create table if not exists %s.%s (
                        pid bigint default nextval('%s.seq_id') primary key,
                        name VARCHAR (255) NOT NULL,
                        gender VARCHAR (255),
                        age int,
                        address VARCHAR(255)
                    )""" %(schema, self.tb_name_person, schema)
            self.db.sql_worker(sql, True, False)

        # create a table for user accounts
        sql = "create sequence if not exists user_id as bigint"
        self.db.sql_worker(sql, True, False)
        sql = """create table if not exists %s (
                    id bigint default nextval('user_id') primary key,
                    name VARCHAR (255) NOT NULL,
                    password VARCHAR (255) NOT NULL,
                    email VARCHAR (255)
                )""" %(self.tb_name_user)
        self.db.sql_worker(sql, True, False)


    def record_access(self, schema, pid, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
        sql = "insert into %s.%s values(default, '%s', '%s')" %(schema, self.tb_name_access, pid, timestamp)
        self.db.sql_worker(sql, True, False)

    def remove(self, schema, pid):
        sql = "delete from %s.%s where pid=%d"%(schema, self.tb_name, pid)
        self.db.sql_worker(sql, True, False)

    def get_recent_access_record(self, schema, num_record):
        sql = """
        select B.name, B.gender, B.age, A.time
        from %s.%s as A inner join %s.%s as B on A.pid = B.pid
        order by time desc limit %d
        """ %(schema, self.tb_name_access, schema, self.tb_name_person, num_record)
        rows, _ = self.db.sql_worker(sql, False, False)
        return rows

    def drop_tables(self, schema):

        sql = "drop schema %s cascade" %schema
        self.db.sql_worker(sql, True, False)

    def user_register(self, name, password, email):
        sql = "insert into %s (name, password, email) values('%s', '%s', '%s')"%(self.tb_name_user, name, password, email)
        self.db.sql_worker(sql, True, False)
        self.user_name = name
        sql = "create schema if not exists %s" %self.user_name
        self.db.sql_worker(sql, True, False)
        self.create_table(self.user_name)

    def get_password(self, name):
        sql = "select password from %s where name='%s'"%(self.tb_name_user, name)
        rows, _ = self.db.sql_worker(sql, False, False)
        if len(rows) == 0:
            return None
        return rows[0][0]

    def check_user_exists(self, name):
        sql = "select id from %s where name='%s'"%(self.tb_name_user, name)
        rows, _ = self.db.sql_worker(sql, False, False)
        if len(rows) == 0:
            return False
        return True

    def login(self, name, password):
        if not self.check_user_exists(name):
            return False
        pw = self.get_password(name)
        if pw == password:
            self.user_name = name
            return True
        return False

    def get_user_info_by_id(self, user_id):
        sql = "select id, name, email from %s where id='%s'" % (self.tb_name_user, user_id)
        rows, _ = self.db.sql_worker(sql, False, False)
        if len(rows) == 0:
            return None, None, None
        return rows[0]

    def get_user_info(self, name):
        sql = "select id, name, email from %s where name='%s'" % (self.tb_name_user, name)
        rows, _ = self.db.sql_worker(sql, False, False)
        if len(rows) == 0:
            return None
        return rows[0]

    def get_record(self, schema, feature, name, gender, age, begin, end, threshold=0.8):
        if feature is not None:
            sql = "select * from (select name,gender,age,time, %s(feature, array[%s]::real[]) as distance from %s.%s a, %s.%s b, %s.%s c " \
                  "where a.pid = c.pid " \
                  "and a.pid = b.pid " \
                  % (self.distance_udf,
                      ",".join([str(x) for x in feature]),
                     schema, self.tb_name_person,
                     schema, self.tb_name,
                     schema, self.tb_name_access,
                     )

        else:
            sql = "select name,gender,age,time from %s.%s a, %s.%s b, %s.%s c " \
                  "where a.pid = c.pid " \
                  "and a.pid = b.pid " \
                  % (schema, self.tb_name_person,
                     schema, self.tb_name,
                     schema, self.tb_name_access,
                     )
        if name is not None and name != "":
            sql += "and name = '%s' " % name
        if gender is not None and gender != "":
            sql += "and gender = '%s' " % gender
        if age is not None and age != "":
            sql += "and age = %s " % age
        if begin is not None and begin != "":
            sql += "and time >= '%s' " % begin
        if end is not None and end != "":
            sql += "and time <= '%s' " % end
        if feature is not None:
            if self.distance_measure == "squared_l2":
                sql += "order by distance limit 10) as b where distance < %f; " % threshold
            elif self.distance_measure == "dot_product":
                sql += "order by distance desc limit 10) as b where distance > %f; " % 0
            else:
                raise ("distance measure %s is not defined" % self.distance_measure)
        elif begin is not None and begin != "":
            sql += "order by time limit 10;"
        else:
            sql += "order by time desc limit 10;"
        rows,_ = self.db.sql_worker(sql, False, False)
        return rows

    def get_record_family(self, schema, pid, begin=None, end=None):
        sql = "select time, name, address, a.pid from %s.%s a, %s.%s b, %s.%s c " \
              "where a.pid = c.pid " \
              "and a.pid = b.pid " \
              "and address = (select address from %s.%s where pid = %d )" \
              % (schema, self.tb_name_person,
                   schema, self.tb_name,
                   schema, self.tb_name_access,
                   schema, self.tb_name_person,
                   pid)
        if begin is not None and begin != "":
            sql += "and time >= '%s' " % begin
        if end is not None and end != "":
            sql += "and time <= '%s' " % end
        sql += " order by time desc"
        rows, _ = self.db.sql_worker(sql, False, False)
        print "number of record", len(rows)
        return rows


    def reset(self):
        sql = "select name from %s" % self.tb_name_user
        rows, _ = self.db.sql_worker(sql, False, False)
        for row in rows:
            sql = "drop schema if exists %s cascade" % row[0]
            self.db.sql_worker(sql, True, False)
        sql = "delete from %s" % self.tb_name_user
        self.db.sql_worker(sql, True, False)
