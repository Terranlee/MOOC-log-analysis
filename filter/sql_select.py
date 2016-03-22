# select user profile from edxapp database
import json

class ProfileDB(object):
    """docstring for ProfileDB"""
    def __init__(self, cid):
        super(ProfileDB, self).__init__()
        self.db_host = '10.9.10.234'
        self.db_port = 3307
        self.db_name = 'edxapp'
        self.db_user = 'readonly'
        self.db_pass = ''

        self.result_dir = '../result/'
        self.c_id = cid

    def get_version(self):
        '''
            get the version of python
            use MySQLdb for python2.7
            use pymysql for python3.4
        '''
        import platform
        return platform.python_version()

    def select_profile_version2(self, uids):
        import MySQLdb
        result = list()
        try:
            conn = MySQLdb.connect(host=self.db_host, port=self.db_port, \
                                user=self.db_user, passwd = self.db_pass, \
                                db=self.db_name, charset='utf8')
        except Exception as e:
            print ('error connecting to database')
            print (e)

        try:
            cursor = conn.cursor()
            sql_command = 'select id, user_id, name, nickname from auth_userprofile where user_id = %d'
            n = cursor.executemany(sql_command, uids)
            print ('get %d results' % (n))
            for row in cursor.fetchall():
                result.append(row)
            cursor.close()
            conn.commit()
            conn.close()
        except Exception as e:
            print ('error operating database')
            print (e)

        return result

    def select_profile_version3(self, uids):
        import pymysql
        result = list()
        try:
            conn = pymysql.connect(host=self.db_host, port=self.db_port, \
                                user=self.db_user, passwd=self.db_pass, \
                                db=self.db_name, charset='utf8')
        except Exception as e:
            print ('error connecting to database')
            print (e)

        try:
            cur = conn.cursor()
            sql_command = 'select id, user_id, name, nickname from auth_userprofile where user_id = %d'
            n = cursor.executemany(sql_command, uids)
            print ('get %d results' % (n))
            for row in cursor.fetchall():
                result.append(row)
            cursor.close()
            conn.commit()
            conn.close()
        except Exception as e:
            print ('error operating database')
            print (e)
        return result

    def load_uids(self):
        filename = self.result_dir + self.c_id + '.namemap'
        try:
            mapping = json.loads(open(filename).read(), strict=False)
        except(ValueError, KeyError):
            print ('error loading data file')
        uids = [for i in mapping]
        return uids

    def select_profile(self, uids):
        version = self.get_version()
        if version[0] == '2':
            result = self.select_profile_version2(uids)
        elif version[0] == '3':
            result = self.select_profile_version3(uids)

        filename = self.result_dir + self.c_id + '.allnames'
        output = open(filename, 'w', encoding='utf-8')
        output.write(json.dumps(result, ensure_ascii=False) + '\n')
        output.close()

def main():
    db = ProfileDB('20740042X')
    uids = db.load_uids()
    db.select_profile(uids)

if __name__ == '__main__':
    main()
