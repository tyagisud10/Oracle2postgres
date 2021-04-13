#!/usr/bin/env python3

"""
Migrates data from source databases on an Oracle system to target schemas on
a Postgres system.

Running the script will delete the target database before recreating it, so
use with caution!
"""
import sys
from oracle2postgres import Oracle2Postgres

def main():
    """
    Connects to the source and target databases, then migrates a list of defined schema.
    """
    msg =  """
    ----------------------------------------------------- \n
    Running this script will delete the target database!  \n
    And it will close connections on the target database. \n
    Are you sure you wish to continue? (y/n)              \n
    ----------------------------------------------------- \n
    \n"""

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
        'trial_run': True,
        'batch_size': 20,
        'processes': None,
        'multiprocess': 'False',
        'debug': 'False'
    }

    migration = Oracle2Postgres(source_config, target_config, migration_config)
    # check the schema exist on the source database
    source = migration.source_connection()
    # check and remove null characters in strings
    oracle2postgres.check_for_nulls(source_engine,source_config['schema_list'],remove=True)

    target = migration.target_connection()
    # target_engine = oracle2postgres.connect_to_target(target_config)
    oracle2postgres.drop_connections(target_config['database'],target_engine)
    oracle2postgres.drop_database(target_config['database'],target_engine)
    oracle2postgres.create_database(target_config['database'],target_engine)



    # create the schema on the target database
    target_engine = oracle2postgres.connect_to_target(target_config,target_config['database'])
    oracle2postgres.create_target_schema(source_config['schema_list'],source_engine,target_engine)

    migration.run()

    # check results
    source_engine = oracle2postgres.connect_to_source(source_config)
    target_engine = oracle2postgres.connect_to_target(target_config, target_config['database'])
    oracle2postgres.check_migration(source_engine, target_engine, source_config)

if __name__ == "__main__":
    """
    Execute when run as script
    """
    main()
