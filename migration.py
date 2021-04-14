from oracle import Oracle
from postgres import Postgres

class Migration(object):
    def __init__(self, source_config, target_config, migration_config):
        self.source_config = source_config
        self.target_config = target_config
        self.migration_config = migration_config
        # setup other classes
        self.source = Oracle(source_config)
        self.target = Postgres(target_config)
        # create connections to dbs and maybe run a quick test
        self.source_engine = self.source.connect()
        self.source.check_schema_exists()
        self.source.check_for_nulls()
        self.target_engine = self.target.connect()

    def schema(self):
        # oracle2postgres.create_target_schema(source_config['schema_list'],source_engine,target_engine)
        pass

    def run(self):
        pass

    def check(self):
        pass
