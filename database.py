import hashlib
import json
import time
import sqlite3 as sql


def get_head(email):
    return 'https://s.gravatar.com/avatar/' + hashlib.md5(email.lower().encode()).hexdigest() + '?s=144'


class DataBase:
    def __init__(self):
        self.file_db_init = "db_init.sql"
        self.file_room_init = "room_init.sql"
        self.secret = "This program is owned by Lance."

        self.error_preview = "发生错误："
        self.success = 'Success.'

        self.error = {
            "Success": "%s" % self.success,
            "Error": "%s 服务器内部错误...请提交BUG给管理员。" % self.error_preview,
            "Auth": "%s Auth 错误，请重新登录。" % self.error_preview,
            "Password": "%s 密码错误。" % self.error_preview,
            "NoUser": "%s 没有这个用户。" % self.error_preview,
        }
        self.errors = {
            "Success": str(0),
            "Error": str(1),
            "Auth": str(2),
            "Password": str(7),
            "NoUser": str(9),
        }
        self.error_messages = {
            str(0): self.error["Success"],
            str(1): self.error["Error"],
            str(2): self.error["Auth"],
            str(7): self.error["Password"],
            str(9): self.error["NoUser"]
        }
        self.tables = ['users', 'files']

        self.sql_types = {"SQLite": 0, "PostgreSQL": 1}
        self.sql_type = self.sql_types['SQLite']
        self.sql_chars = ["?", "%s"]
        self.sql_char = self.sql_chars[self.sql_type]

        self.conn = None
        self.connect_init()

    def connect_init(self):
        self.conn = sql.connect('data_sql.db', check_same_thread=False)

    def v(self, string: str):
        return string.replace('%s', self.sql_char)

    def cursor_get(self):
        cursor = self.conn.cursor()
        return cursor

    def cursor_finish(self, cursor):
        self.conn.commit()
        cursor.close()

    def make_result(self, code, **args):
        result = {
            "code": str(code),
            "message": self.error_messages[str(code)],
            "data": args
        }
        return json.dumps(result)

    def check_in(self, table, line, value):
        cursor = self.cursor_get()
        try:
            cursor.execute("SELECT %s FROM %s WHERE %s = \'%s\'" % (line, table, line, value))
        except Exception as e:
            print(e)
            return False
        result = cursor.fetchall()
        self.cursor_finish(cursor)
        if len(result) > 0:
            return True
        return False

    def db_init(self):
        try:
            cursor = self.cursor_get()
            for table in self.tables:
                try:
                    cursor.execute("DROP TABLE IF EXISTS %s" % table)
                except Exception as e:
                    print('Error when dropping:', table, '\nException:\n', e)
                    self.cursor_finish(cursor)
                    cursor = self.cursor_get()
            self.cursor_finish(cursor)
        except Exception as e:
            print(e)
        self.conn.close()
        self.connect_init()
        cursor = self.cursor_get()
        # 一次只能执行一个语句。需要分割。而且中间居然不能有空语句。。
        with open(self.file_db_init, encoding='utf8') as f:
            string = f.read()
            for s in string.split(';'):
                try:
                    if s != '':
                        cursor.execute(s)
                except Exception as e:
                    print('Error:\n', s, 'Exception:\n', e)
        self.cursor_finish(cursor)

    def create_user(self, username='Lance', password='',
                    email='lanceliang2018@163.com'):
        if self.check_in("users", "username", username):
            return self.make_result(self.errors["UserExist"])

        cursor = self.cursor_get()

        password = hashlib.md5(password.encode()).hexdigest()
        cursor.execute(self.v("INSERT INTO users "
                              "(username, password, email) "
                              "VALUES (%s, %s, %s)"),
                       (username, password, email))

        self.cursor_finish(cursor)
        return self.make_result(0)

    # 检查密码是否符合
    def user_check(self, username, password):
        if self.check_in("users", "username", username) is False:
            return False
        cursor = self.cursor_get()
        password = hashlib.md5(password.encode()).hexdigest()
        cursor.execute(self.v("SELECT password FROM users WHERE username = %s"), (username,))
        data = cursor.fetchall()
        if len(data) == 0:
            return False
        storage = data[0][0]
        # print(storage)
        self.cursor_finish(cursor)
        if storage == password:
            return True
        return False

    # 创建鉴权避免麻烦。鉴权格式：MD5(username, secret, time)
    def create_auth(self, username, password):
        cursor = self.cursor_get()
        if not self.user_check(username, password):
            return self.make_result(self.errors["Password"])
        string = "%s %s %s" % (username, self.secret, str(time.time()))
        auth = hashlib.md5(string.encode()).hexdigest()

        cursor.execute(self.v("UPDATE users SET auth = %s WHERE username = %s"), (auth, username))

        self.cursor_finish(cursor)
        return self.make_result(0, auth={'auth': auth})

    def check_auth(self, auth):
        result = self.check_in("users", "auth", auth)
        if result is True:
            return True
        return False

    def auth2username(self, auth):
        if self.check_auth(auth) is False:
            return 'No_User'
        cursor = self.cursor_get()
        cursor.execute(self.v("SELECT username FROM users WHERE auth = %s"), (auth,))
        username = cursor.fetchall()[0][0]
        self.cursor_finish(cursor)
        return username

    def user_set_info(self, auth, email: str = None):
        if self.check_auth(auth) is False:
            return self.make_result(self.errors["Auth"])
        cursor = self.cursor_get()
        username = self.auth2username(auth)
        if email is not None:
            cursor.execute(self.v("UPDATE users SET email = %s WHERE username = %s"), (email, username))
        self.cursor_finish(cursor)
        return self.make_result(0)

    def file_upload(self, auth, filename: str = 'FILE', url: str = '', filesize: int=0):
        if self.check_auth(auth) is False:
            return self.make_result(self.errors["Auth"])
        username = self.auth2username(auth)
        cursor = self.cursor_get()
        uptime = int(time.time())
        cursor.execute(self.v("INSERT INTO files (username, filename, url, uptime, filesize) "
                              "VALUES (%s, %s, %s, %s, %s)"),
                       (username, filename, url, str(uptime), filesize))
        self.cursor_finish(cursor)
        return self.make_result(0)

    def file_get(self, auth):
        if self.check_auth(auth) is False:
            return self.make_result(self.errors["Auth"])
        username = self.auth2username(auth)
        cursor = self.cursor_get()
        cursor.execute(self.v("SELECT DISTINCT username, filename, url, uptime, filesize FROM files "
                              "WHERE username = %s ORDER BY filename "),
                       (username, ))
        data = cursor.fetchall()
        self.cursor_finish(cursor)
        result = []
        for d in data:
            result.append({'username': d[0], 'filename': d[1], 'url': d[2], 'uptime': d[3], 'filesize': d[4]})
        return self.make_result(0, files=result)


def jsonify(string: str):
    return json.loads(string)


if __name__ == '__main__':
    db = DataBase()
    db.db_init()
    db.create_user(username='', password='')
    _au = db.create_auth(username='', password='')
    print(_au)
    _au = jsonify(_au)['data']['auth']['auth']

    print(db.file_upload(_au, filename='Name', filesize=32, url='https://baidu.com/index.html'))
    print(db.file_get(_au))
