#!/usr/bin/env python3
from migration import Migration

source_config = {
    'username': 'hr',
    'host': 'localhost',
    'port': 1521,
    'database': 'orcl',
    'password': 'oracle',
    'schema_list': ['hr']
}

target_config = {
    'username': 'sudh',
    'host': 'localhost',
    'port': 5432,
    'database': "hr",
    'password': 'sudh@123'
}

migration_config = {
    'load_type': True,
    'trialrun': True,
    'batchsize': '10',
    'logged': False,
    'multiprocess': True,
    'processes': None
}

# validate all the configuration!
# this configuration will be passed by the frontend in some way or the other
def validate():
    # clean_test will come here!
    pass

migration = Migration(source_config, target_config, migration_config)
migration.schema()
migration.run()
migration.check()
