class Oracle(object):
    def __init__(self, config):
        self.config = config

    def connect(self):
        dsn_str = cx_Oracle.makedsn(self.config['host'],self.config['port'],service_name=self.config['database'])
        con_string = 'oracle://{}:{}@'.format(self.config['username'], self.config['password']) + dsn_str
        return sqlalchemy.create_engine(con_string)

    def check_schema_exist(self):
        pass

    def check_for_nulls(self):
        pass

    def get_schema():
        # return schema
        pass
