# -*- coding: utf8 -*-

import sys
import urllib
import urllib2
import json
import datetime
from django.conf import settings


def debug(msg, code=None):
    if settings.enable_debug:
        if code is None:
            print "message: %s" % msg
        else:
            print "message: %s, code: %s " % (msg, code)


AUTHOR_MAIL = "uberurey_ups@163.com"

weixin_qy_CorpID = settings.WX_CORPID
weixin_qy_Secret = settings.WX_SECRET

def sqlite3_execute(database, sql):
    try:
        sql_conn = sqlite3_conn(database)
        sql_cursor = sql_conn.cursor()
        sql_cursor.execute(sql)
        sql_conn.commit()
        sql_conn.close()
    except sqlite3.Error as e:
        print e
        sys.exit(1)


def sqlite3_create_table_token():
    sql_conn = sqlite3_conn(sqlite3_db_file)
    sql_cursor = sql_conn.cursor()
    sql_cursor.execute('''CREATE TABLE "main"."weixin_token" (
                "id"  INTEGER ,
                "access_token"  TEXT,
                "expires_in"  TEXT,
                "expires_on"  TEXT,
                "is_expired"  INTEGER
                )
                ;
    ''')
    sqlite3_commit(sql_conn)
    sqlite3_close(sql_conn)


def sqlite3_create_table_account():
    sql_conn = sqlite3_conn(sqlite3_db_file)
    sql_cursor = sql_conn.cursor()
    sql_cursor.execute('''CREATE TABLE "main"."weixin_account" (
                "id"  INTEGER,
                "name"  TEXT,
                "corpid"  TEXT,
                "secret"  TEXT,
                "current"  INTEGER
                )
                ;
    ''')
    sqlite3_commit(sql_conn)
    sqlite3_close(sql_conn)


def sqlite3_create_tables():
    print "sqlite3_create_tables"
    sql_conn = sqlite3_conn(sqlite3_db_file)
    sql_cursor = sql_conn.cursor()
    sql_cursor.execute('''CREATE TABLE "main"."weixin_token" (
                "id"  INTEGER ,
                "access_token"  TEXT,
                "expires_in"  TEXT,
                "expires_on"  TEXT,
                "is_expired"  INTEGER
                )
                ;
    ''')
    sql_cursor.execute('''CREATE TABLE "main"."weixin_account" (
                "id"  INTEGER,
                "name"  TEXT,
                "corpid"  TEXT,
                "secret"  TEXT,
                "current"  INTEGER
                )
                ;
    ''')
    sqlite3_commit(sql_conn)
    sqlite3_close(sql_conn)


def sqlite3_set_credential(corpid, secret):
    try:
        sql_conn = sqlite3_conn(sqlite3_db_file)
        sql_cursor = sql_conn.cursor()
        sql_cursor.execute('''INSERT INTO "weixin_account" ("id", "name", "corpid", "secret", "current") VALUES
                                (1,
                                'odbp',
                                ?,
                                ?,
                                1)
''', (corpid, secret))
        sqlite3_commit(sql_conn)
        sqlite3_close(sql_conn)
    except sqlite3.Error:
        sqlite3_create_table_account()
        sqlite3_set_credential(corpid, secret)


def sqlite3_set_token(access_token, expires_in, expires_on, is_expired):
    try:
        sql_conn = sqlite3_conn(sqlite3_db_file)
        sql_cursor = sql_conn.cursor()
        sql_cursor.execute('''INSERT INTO "weixin_token"
                              ("id", "access_token", "expires_in", "expires_on", "is_expired") VALUES
                              (
                              1,
                              ?,
                              ?,
                              ?,
                              ?
                              )
''', (access_token, expires_in, expires_on, is_expired))
        sqlite3_commit(sql_conn)
        sqlite3_close(sql_conn)
    except sqlite3.Error:
        sqlite3_create_table_token()
        sqlite3_set_token(access_token, expires_in, expires_on, is_expired)


def sqlite3_get_credential():
    try:
        sql_conn = sqlite3_conn(sqlite3_db_file)
        sql_cursor = sql_conn.cursor()
        credential = sql_cursor.execute('''SELECT "corpid", "secret"  FROM weixin_account WHERE current == 1;''')
        result = credential.fetchall()
        sqlite3_close(sql_conn)
    except sqlite3.Error:
        sqlite3_set_credential(weixin_qy_CorpID, weixin_qy_Secret)
        return sqlite3_get_credential()
    else:
        if result is not None and len(result) != 0:
            return result
        else:
            print "unrecoverable problem, please alter to %s" % AUTHOR_MAIL
            sys.exit(1)


def sqlite3_get_token():
    try:
        sql_conn = sqlite3_conn(sqlite3_db_file)
        sql_cursor = sql_conn.cursor()
        credential = sql_cursor.execute(
            '''SELECT "access_token", "expires_on" FROM weixin_token WHERE "is_expired" == 1 ;''')
        result = credential.fetchall()
        sqlite3_close(sql_conn)
    except sqlite3.Error:
        info = sys.exc_info()
        print info[0], ":", info[1]
    else:
        if result is not None and len(result) != 0:
            return result
        else:
            # print "unrecoverable problem, please alter to %s" % AUTHOR_MAIL
            # sys.exit(1)
            return None


def sqlite3_update_token(access_token, expires_on):
    sql_conn = sqlite3_conn(sqlite3_db_file)
    sql_cursor = sql_conn.cursor()
    sql_cursor.execute('''UPDATE "weixin_token" SET
                          access_token=?,
                          expires_on=?
                          WHERE _ROWID_ = 1;''', (access_token, expires_on)
                       )
    sqlite3_commit(sql_conn)
    sqlite3_close(sql_conn)


class WeiXinTokenClass(object):
    def __init__(self):
        self.__corpid = None
        self.__corpsecret = None
        self.__use_persistence = True

        self.__access_token = None
        self.__expires_in = None
        self.__expires_on = None
        self.__is_expired = None

        if self.__use_persistence:
            self.__corpid = sqlite3_get_credential()[0][0]
            self.__corpsecret = sqlite3_get_credential()[0][1]
        else:
            self.__corpid = weixin_qy_CorpID
            self.__corpsecret = weixin_qy_Secret

    def __get_token_from_weixin_qy_api(self):
        parameters = {
            "corpid": self.__corpid,
            "corpsecret": self.__corpsecret
        }
        url_parameters = urllib.urlencode(parameters)
        token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?"
        url = token_url + url_parameters
        response = urllib2.urlopen(url)
        result = response.read()
        token_json = json.loads(result)
        if token_json['access_token'] is not None:
            get_time_now = datetime.datetime.now()
            # TODO(Guodong Ding) token will expired ahead of time or not expired after the time
            expire_time = get_time_now + datetime.timedelta(seconds=token_json['expires_in'])
            token_json['expires_on'] = str(expire_time)
            self.__access_token = token_json['access_token']
            self.__expires_in = token_json['expires_in']
            self.__expires_on = token_json['expires_on']
            self.__is_expired = 1

            try:
                token_result_set = sqlite3_get_token()
            except sqlite3.Error:
                token_result_set = None
            if token_result_set is None and len(token_result_set) == 0:
                sqlite3_set_token(self.__access_token, self.__expires_in, self.__expires_on, self.__is_expired)
            else:
                if self.__is_token_expired() is True:
                    sqlite3_update_token(self.__access_token, self.__expires_on)
                else:
                    debug("pass")
                    return
        else:
            if token_json['errcode'] is not None:
                print "errcode is: %s" % token_json['errcode']
                print "errmsg is: %s" % token_json['errmsg']
            else:
                print result

    def __get_token_from_persistence_storage(self):
        try:
            token_result_set = sqlite3_get_token()
        except sqlite3.Error:
            self.__get_token_from_weixin_qy_api()
        finally:
            if token_result_set is None:
                self.__get_token_from_weixin_qy_api()
                token_result_set = sqlite3_get_token()
                access_token = token_result_set[0][0]
                expire_time = token_result_set[0][1]
            else:
                access_token = token_result_set[0][0]
                expire_time = token_result_set[0][1]
        expire_time = datetime.datetime.strptime(expire_time, '%Y-%m-%d %H:%M:%S.%f')
        now_time = datetime.datetime.now()
        if now_time < expire_time:
            # print "The token is %s" % access_token
            # print "The token will expire on %s" % expire_time
            return access_token
        else:
            self.__get_token_from_weixin_qy_api()
            return self.__get_token_from_persistence_storage()

    @staticmethod
    def __is_token_expired():
        try:
            token_result_set = sqlite3_get_token()
        except sqlite3.Error as e:
            print e
            sys.exit(1)
        expire_time = token_result_set[0][1]
        expire_time = datetime.datetime.strptime(expire_time, '%Y-%m-%d %H:%M:%S.%f')
        now_time = datetime.datetime.now()
        if now_time < expire_time:
            return False
        else:
            return True

    def get(self):
        return self.__get_token_from_persistence_storage()