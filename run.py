#!/usr/bin/python
from flask import Flask, redirect, url_for, request, Response,jsonify, make_response, render_template
from flask_cors import CORS
import run_migration as migration
import json
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import cx_Oracle
import oracle2postgres


app = Flask(__name__)
CORS(app)

@app.route('/oracle', methods=['GET', 'POST'])
def connect_oracle():
    config = request.data
    config = json.loads(config)
    source_config = config['source_config']
    oracle2postgres.connect_to_source(source_config)
    # inspector = sqlalchemy.inspect(source_engine)
    return jsonify(
        message='Connection successful'), 200

@app.route('/oracle-getSchema', methods=['GET', 'POST'])
def connect_oracle_getSchema():
    config = request.data
    config = json.loads(config)
    source_config = config['source_config']
    source_engine = oracle2postgres.connect_to_source(source_config)
    inspector = sqlalchemy.inspect(source_engine)
    all_schema = inspector.get_schema_names()
    all_schema = list(map(lambda x: {'db': x}, all_schema))
    return jsonify(all_schema)

@app.route('/postgres', methods=['GET', 'POST'])
def connect_postgres():
    config = request.data
    config = json.loads(config)
    target_config = config['target_config']
    target_engine = oracle2postgres.connect_to_target(target_config, target_config['database'])
    # import IPython; IPython.embed()
    print(target_engine)
    return jsonify(
        message='success'), 200



@app.route('/migrate', methods = ['POST'])
def login():
    print(request.json)
    config = request.data
    config = json.loads(config)
    print(config)
    migration.run(config)
    #
    return jsonify(
        message='success'), 200

if __name__ == '__main__':
   app.run(debug = True)
