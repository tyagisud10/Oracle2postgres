import sys
import logging
from datetime import datetime
import multiprocessing
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import cx_Oracle
from sqlalchemy.dialects.postgresql import \
    ARRAY, BIGINT, BIT, BOOLEAN, BYTEA, CHAR, CIDR, DATE, \
    DOUBLE_PRECISION, ENUM, FLOAT, HSTORE, INET, INTEGER, \
    INTERVAL, JSON, JSONB, MACADDR, NUMERIC, OID, REAL, SMALLINT, TEXT, \
    TIME, TIMESTAMP, UUID, VARCHAR, INT4RANGE, INT8RANGE, NUMRANGE, \
    DATERANGE, TSRANGE, TSTZRANGE, TSVECTOR

fn = 'migration.log'
logfile = "logs/{}_{}".format(datetime.now().strftime("%Y_%m_%d"), fn)
logging.basicConfig(filename=logfile, level=logging.INFO)

# Import postgres types


def check_for_nulls(engine, schema_list, remove=False):
    """
    Check for null characters in strings.
    Args:
        engine (obj): Database engine.
        schema_list (list): List of schema to remove.
        remove (bool): Remove null characters, if found. Default False.
    """
    msg = "\t{}: Checking source database for nulls in strings." \
        .format(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"))

    logging.info(msg)
    null_list = []
    con = engine.connect()

    for source_schema in schema_list:
        source_metadata = sqlalchemy.MetaData(engine, quote_schema=True)
        source_metadata.reflect(schema=source_schema)

        # iterate the tables
        for t in source_metadata.sorted_tables:
            for col in t.columns:
                try:
                    result = t.select().where(col.like('%' + chr(0) + '%')).execute()
                    nulls = result.fetchone()
                except:
                    nulls = None
                if nulls and len(nulls):
                    msg = "\t{}: Null characters found in: {}.{}.{}".format(datetime.strftime(datetime.now(), "%Y-%m-%d "
                                                                                                            "%H:%M:%S"),
                                                                          source_schema, t.name, col.name)

                    logging.info(msg)
                    null_list.append('{}.{}.{}'.format(source_schema, t.name, col.name))
                    if remove:
                        # remove them
                        t.update().values({col: sqlalchemy.func.replace(col, chr(0),
                                                                        '')}).where(
                            col.like('%' + chr(0) + '%')).execute()
                        con.execute("COMMIT")
                        msg = "\t{}: Null characters removed from {}.{}.{}".format(
                            datetime.strftime(datetime.now(), "%Y-%m-%d "
                                                              "%H:%M:%S"), source_schema,
                            t.name, col.name)
                        logging.info(msg)

    if null_list and not remove:
        msg = "\tNull chars must be removed from: {}".format(null_list)
        con.close()
        logging.info(msg)
        sys.exit(msg)

    con.close()


def connect_to_source(config):
    """
    Connect to source database.
    Args:
        config (dict): Settings for the source database.
    """
    print_log = False

    dsn_str = cx_Oracle.makedsn(config['host'], config['port'], service_name=config['database'])
    con_string = 'oracle://{}:{}@'.format(config['username'], config['password']) + dsn_str
    engine = sqlalchemy.create_engine(con_string, echo=print_log)

    return engine


def connect_to_target(config, dbname=None):
    """
    Connect to target database.
    Args:
        config (dict): Settings for the target database.
        dbname (str): Name of target database.
    """
    print_log = False

    if dbname:
        con_string = 'postgresql+psycopg2://{}:{}@{}:{}/{}'.format(config['username'],
                                                                   config['password'], config['host'], config['port'],
                                                                   dbname)
    else:
        con_string = 'postgresql+psycopg2://{}:{}@{}:{}'.format(config['username'],
                                                                config['password'], config['host'], config['port'])

    engine = sqlalchemy.create_engine(con_string, echo=print_log)

    return engine


def _clean_list(schema_list):
    """
    check the list of schema is a valid list
    Args:
        schema_list (list): List of schema
    """
    try:
        cleaned = [x.strip(' ') for x in schema_list.split(',')]
    except:
        pass
    return cleaned


def check_schema_exist(engine, schema_list):
    """
    Check the schema are present on the source database
    Args:
        engine (obj): Database engine.
        schema_list (list): List of schema.
    """
    # get list of all schema
    inspector = sqlalchemy.inspect(engine)
    all_schema = inspector.get_schema_names()

    # check schema are in the database
    not_found = [x for x in schema_list if x not in all_schema]

    if not_found:
        msg = "\tThe following schema are not found on the source database: {}".format(not_found)
        logging.info(msg)
        sys.exit(msg)

    msg = '\nList of schema to copy: {}\n'.format(schema_list)
    print(msg)

    return schema_list


def _migrate_data(schema, source_config, target_config, migration_config):
    """
    Migrate the data from the source tables to the target tables
    Args:
        schema (str): Name of schema to migrate.
        source_config (dict): Settings for source database.
        target_config (dict): Settings for target database.
        migration_config (dict): Settings for the migration.
    """
    # create database connections
    source_engine = connect_to_source(source_config)
    target_engine = connect_to_target(target_config, target_config['database'])

    # load the schema metadata profile
    source_metadata = sqlalchemy.MetaData(source_engine)
    source_metadata.reflect(schema=schema)

    # iterate the tables, loading the data
    for t in source_metadata.sorted_tables:
        _copy_data(source_engine, schema, target_engine, t, migration_config['batchsize'],
                   migration_config['logged'], trialrun=migration_config['trialrun'])


def create_target_schema(schema_list, source_engine, target_engine):
    """
    Recreate the sources tables on the target database
    Args:
        schema_list (list): List of schema.
        source_engine (obj): Database engine.
        target_engine (obj): Database engine.
    """
    msg = 'Creating schema on target database...\n'
    print(msg)
    for source_schema in schema_list:

        # load the schema metadata profile
        print(source_schema)
        source_metadata = sqlalchemy.MetaData(source_engine, quote_schema=True)
        source_metadata.reflect(schema=source_schema)

        # create the schema on the target database
        target_engine.execute(sqlalchemy.schema.CreateSchema(source_schema))

        # iterate the tables
        for t in source_metadata.sorted_tables:

            # clear the indexes and constraints
            t.indexes.clear()
            t.constraints.clear()

            # clean the data types
            for col in t.columns:

                # set the column types
                newtype = _convert_type(col.name, col.type,
                                        schema_name=source_schema, table_name=t.name)
                t.c[col.name].type = newtype

                # check the default values
                if t.c[col.name].default:
                    new_default = _check_default(t.c[col.name].default)
                    t.c[col.name].default = new_default

                # remove the server_default values
                if t.c[col.name].server_default:
                    t.c[col.name].server_default = None

                    # Build the tables on the target database
        source_metadata.create_all(target_engine, checkfirst=False)

        msg = "\t{}: Target schema created: {}".format(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"),
                                                     source_schema)
        logging.info(msg)


def drop_connections(dbname, engine):
    """
    Closes connections to a database to avoid any interference
    with the migration.
    Args:
        dbname (str): Name of database.
        engine (obj): Database engine.
    """
    con = engine.connect()
    con.execute("COMMIT")  # need to close current transaction
    con.execute("""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = '{}';""".format(dbname))
    con.execute("COMMIT")  # need to close current transaction
    con.close()


def drop_database(dbname, engine):
    """
    Warning, drops the specified database!
    Args:
        dbname (str): Name of database to drop.
        engine (obj): Database engine.
    """

    # msg =  """
    # --------------------------------------------------------- \n
    # Warning, you are about to delete the following database!  \n
    # {}.{}
    # Are you sure you wish to continue?                        \n
    # Type 'yes' to proceed.                                    \n
    # --------------------------------------------------------- \n
    # \n""".format(engine.name,dbname)
    #
    # if input(msg).lower() != "yes":
    #     sys.exit()

    con = engine.connect()
    con.execute("COMMIT")  # need to close current transaction
    con.execute("DROP DATABASE IF EXISTS {}".format(dbname))
    con.execute("COMMIT")  # need to close current transaction
    con.close()
    msg = "\t{}: Target database dropped: {}".format(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"), dbname)
    logging.info(msg)


def create_database(dbname, engine):
    """
    Creates a new database on the target.
    Args:
        dbname (str): Name of database.
        engine (obj): Database engine.
    """
    con = engine.connect()
    con.execute("COMMIT")  # need to close current transaction
    con.execute("CREATE DATABASE {}".format(dbname))
    con.execute("COMMIT")
    con.close()
    msg = "\t{}: Target database created: {}".format(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"), dbname)
    logging.info(msg)


def _check_default(default):
    new_default = default
    logging.info("CHECKING DEFAULT")

    if str(default).lower() == "sysdate":
        logging.info("UPDATED")
        new_default = None

    return new_default


def _insert_data(target_session, table, data):
    """
    Inserts the data into the target system. Disables integrity checks 
    prior to inserting.
    Args:
        target_session (obj): SQLAlchemy session.
        table (obj): SQLAlchemy table object.
        data (obj): SQLAlchemy data object.
    """
    if data:
        # disable integrity checks
        target_session.execute("SET session_replication_role = replica;")
        # insert data
        target_session.execute(table.insert(), data)
        # enable integrity checks
        target_session.execute("SET session_replication_role = DEFAULT;")
        target_session.commit()


def _get_column_string(table):
    """
    Create a string of column names for contructing a query.
    Args:
        table (obj): SQLAlchemy table object.
    """
    column_list = table.columns.keys()

    # quote columns that are also keywords. 
    # assume they are upper case!
    keywords = ['where', 'from', 'select', 'comment', 'order']
    column_list = ['"{}"'.format(x.upper()) if x.lower() in keywords else x for x in column_list]
    column_str = ', '.join(column_list)

    return column_str


def _copy_data(source_engine,source_schema,target_engine,table,
               batchsize=10000,logged=True,trialrun=False):
    """
    Copies the data into the target system. Disables integrity checks
    prior to inserting.
    Args:
        source_engine (obj): Database engine.
        source_schema (obj): Name of schema to migrate.
        target_engine (obj): Database engine.
        table (obj): SQLAlchemy table object.
        batchsize (int): Number of rows to migrate in each batch.
        logged (bool): Enable or disable Postgres logging.
        trialrun (bool): Run in trial mode.
    """
    # create sessions

    SourceSession = sessionmaker(bind=source_engine)
    source_session = SourceSession()
    TargetSession = sessionmaker(bind=target_engine)
    target_session = TargetSession()

    # print schema
    msg = '\tBegan copy of {}.{} at {}'.format(source_schema,table.name,
                                             datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S"))
    logging.info(msg)

    target_session.execute("SET SEARCH_PATH TO {};".format(source_schema))

    # switch off logging
    logswitch = False
    if not logged:
        try:
            target_session.execute('ALTER TABLE "{}" SET UNLOGGED'.format(table.name))
            logswitch = True
        except:
            target_session.rollback()
            target_session.execute("SET SEARCH_PATH TO {};".format(source_schema))
            msg = "Unable to disable logging for {}.{}".format(source_schema,table.name)
            logging.info(msg)

    columns = _get_column_string(table)

    # # copy the data in batches
    # if trialrun:
    #     r = source_session.query(table).limit(200)
    #     data = r.all()
    #     _insert_data(target_session,table,data)
    # else:
    #     for data in source_session.query(table).yield_per(batchsize):
    #         _insert_data(target_session,table,data)

    # get the initial data batch
    offset = 0
    query =  """SELECT {} 
                FROM {}.{} 
                ORDER BY rowid 
                OFFSET {} ROWS 
                FETCH NEXT {} ROWS ONLY""".format(columns,source_schema,
                                                  table.name,offset,batchsize)
    data = source_session.execute(query).fetchall()

    while data:
        # insert the data
        _insert_data(target_session,table,data)

        # print summary
        msg = '\tCopied rows {}-{} of {}.{} at {}'.format(offset,offset+batchsize,
            source_schema,table.name, datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S"))
        logging.info(msg)

        # break after a couple of loops
        if trialrun and offset > 10:
            break

        # update the offset
        offset = offset + batchsize
        query =  """SELECT {} 
                    FROM {}.{} 
                    ORDER BY rowid 
                    OFFSET {} ROWS 
                    FETCH NEXT {} ROWS ONLY""".format(columns,source_schema,
                                                      table.name,offset,batchsize)

        # load the next chunk of data
        try:
            data = source_session.execute(query).fetchall()
        except:
            # break if end of table is reached
            data = None
            break

    # switch on database logging
    if logswitch:
        target_session.execute('ALTER TABLE "{}" SET LOGGED'.format(table.name))

    # record end
    msg = '\tFinished copy of {}.{} at {}'.format(source_schema,table.name,
                                                datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S"))
    logging.info(msg)

    # close the sessions
    source_session.close()
    target_session.close()


def _convert_type(colname, ora_type, schema_name='',
                  table_name=''):
    """
    Converts a data type in the source (Oracle) database to a Postgres type.
    Args:
        colname (str): Name of the column.
        ora_type (obj): Data type in the source (Oracle) database.
        schema_name (str): Name of the schema.
        table_name (str): Name of the table.
    """
    pg_type = ora_type

    # "NullType is used as a default type for those cases 
    # where a type cannot be determined"
    # NB: this needs to be first in the list
    # Otherwise str(ora_type) clauses will error
    if isinstance(ora_type, sqlalchemy.types.NullType):
        pg_type = sqlalchemy.types.String()
        logging.info('\t{}.{}.{}: NULL DETECTED'.format(schema_name, table_name,
                                                        colname))
        return pg_type
    elif isinstance(ora_type, sqlalchemy.types.Numeric):
        pg_type = sqlalchemy.types.Numeric()
    elif isinstance(ora_type, sqlalchemy.types.DateTime):
        pg_type = TIMESTAMP()
    elif isinstance(ora_type, sqlalchemy.types.Text):
        pg_type = sqlalchemy.types.Text()
    elif isinstance(ora_type, sqlalchemy.types.NVARCHAR):
        pg_type = sqlalchemy.types.VARCHAR()
    elif isinstance(ora_type, sqlalchemy.types.BLOB):
        pg_type = BYTEA()
    elif str(ora_type) == 'RAW':
        pg_type = BYTEA()
    # this isn't currently catching the binary_float
    elif str(ora_type) == 'BINARY_FLOAT':
        pg_type = REAL()
    elif str(ora_type) == 'INTERVAL DAY TO SECOND':
        pg_type = sqlalchemy.types.Interval(second_precision=True)
    else:
        pass

    if pg_type != ora_type:
        msg = "\t{}.{}.{}: {} converted to {}".format(schema_name, table_name,
                                                      colname, ora_type, pg_type)
        logging.info(msg)

    return pg_type


def migrate(source_config, target_config, migration_config):
    """
    Migrate data from the source database to the target database. The target
    database and schema must already exist.
    Args:
        source_config (dict): Settings for source database.
        target_config (dict): Settings for target database.
        migration_config (dict): Settings for the migration.
    """
    msg = '\tMigrating data to target database...\n'
    print(msg)

    # set up multiprocessing
    if migration_config['multiprocess']:

        # set number of processes
        if migration_config['processes']:
            pool = multiprocessing.Pool(int(migration_config['processes']))
        else:
            pool = multiprocessing.Pool()

        # starmap takes an iterable list
        arg_iterable = [[schema, source_config, target_config, migration_config] for schema in
                        source_config['schema_list']]
        pool.starmap(_migrate_data, arg_iterable)
    else:
        for schema in source_config['schema_list']:
            _migrate_data(schema, source_config, target_config, migration_config)

    msg = '\tMigration complete!\n'
    logging.info(msg)
    print(msg)


def check_migration(source_engine, target_engine, source_config):
    """
    Carry out post migration integrity checks.
    Args:
        source_engine (obj): Database engine.
        target_engine (obj): Database engine.
        source_config (dict): Settings for source database.
    """
    msg = '\tChecking migration.\n'
    print(msg)
    logging.info(msg)

    # create dict of metadata, with schema_name as key.
    source_table_details = {}

    SourceSession = sessionmaker(bind=source_engine)
    source_session = SourceSession()
    TargetSession = sessionmaker(bind=target_engine)
    target_session = TargetSession()

    # iterate the source schema to populate source_details
    for schema_name in source_config['schema_list']:
        source_metadata = sqlalchemy.MetaData(source_engine, quote_schema=True)
        source_metadata.reflect(schema=schema_name)
        # source_table_details[schema_name] = source_metadata.tables

        target_metadata = sqlalchemy.MetaData(target_engine, quote_schema=True)
        target_metadata.reflect(schema=schema_name)

        for t in source_metadata.sorted_tables:
            # compare row count
            _compare_row_count(schema_name, source_session, target_session, t, logging)

    # close the sessions
    source_session.close()
    target_session.close()


def _compare_row_count(schema_name, source_session, target_session, t, logging):
    """
    Compare row counts for a table on different sources.
    Args:
        source_session (obj): Database session.
        target_session (obj): Database session.
        t (obj): SQLAlchemy table object.
    """
    # count the rows
    try:
        source_row_ct = source_session.query(t).count()
        target_row_ct = target_session.query(t).count()
    except:
        msg = "\t{}.{}: Error counting rows.".format(schema_name, t.name)
        logging.error(msg)

    # compare the rows
    try:
        if source_row_ct == target_row_ct:
            msg = "\t{}.{}: Source and target row count matches ({} rows)".format(schema_name,
                                                                                t.name, source_row_ct)
            logging.info(msg)
        else:
            msg = "\t{}.{}: Source has {} rows. Target has {} rows.".format(schema_name,
                                                                          t.name, source_row_ct, target_row_ct)
            logging.warning(msg)
    except:
        msg = "\t{}.{}: Unable to compare row counts.".format(schema_name, t.name)
        logging.error(msg)
