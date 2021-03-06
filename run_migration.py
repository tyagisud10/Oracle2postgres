#!/usr/bin/python

"""
Migrates data from source databases on an Oracle system to target schemas on
a Postgres system.

Running the script will delete the target database before recreating it, so
use with caution!
"""
import sys
import oracle2postgres

def run(config):

    #oracle2postgres.create_logfile()

    # get settings for migration
    source_config = config['source_config']
    target_config = config['target_config']
    migration_config = config['migration_config']

    # check the schema exist on the source database
    source_engine = oracle2postgres.connect_to_source(source_config)
    oracle2postgres.check_schema_exist(source_engine,source_config['schema_list'])

    # check and remove null characters in strings
    oracle2postgres.check_for_nulls(source_engine,source_config['schema_list'],remove=True)


    target_engine = oracle2postgres.connect_to_target(target_config)
    oracle2postgres.drop_connections(target_config['database'],target_engine)
    oracle2postgres.drop_database(target_config['database'],target_engine)
    oracle2postgres.create_database(target_config['database'],target_engine)



    # create the schema on the target database
    target_engine = oracle2postgres.connect_to_target(target_config,target_config['database'])
    if migration_config['load_type'] == 'P' or migration_config['load_type'] == 'F':
        oracle2postgres.create_target_schema(source_config['schema_list'],source_engine,target_engine)

    if migration_config['load_type'] == "F" or migration_config['load_type'] == "D":
        oracle2postgres.migrate(source_config, target_config, migration_config)

    # check results
    source_engine = oracle2postgres.connect_to_source(source_config)
    target_engine = oracle2postgres.connect_to_target(target_config, target_config['database'])
    oracle2postgres.check_migration(source_engine, target_engine, source_config)
