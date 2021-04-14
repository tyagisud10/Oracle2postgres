#!/usr/bin/python
from flask import Flask, redirect, url_for, request, Response,jsonify, make_response


import run_migration as migration
import json


app = Flask(__name__)

# configuration = {
#     'source_config' = {
#         'username': 'hr',
#         'host': 'localhost',
#         'port': 1521,
#         'database': 'orcl',
#         'password': 'oracle',
#         'schema_list': ['hr']
#     },
#
#     'target_config' = {
#         'username': 'sudh',
#         'host': 'localhost',
#         'port': 5432,
#         'database': "hr",
#         'password': 'sudh@123'
#     },
#
#     'migration_config' = {
#         'load_type': True,
#         'trialrun': True,
#         'batchsize': '10',
#         'logged': False,
#         'multiprocess': True,
#         'processes': None
#     }
# }



# @app.route('/start')
# def start():
#    return 'Starting migration!'
#
# @app.route('/end')
# def end():
#     return 'Ending Migration!'

@app.route('/login', methods = ['POST'])
def login():
    config = request.data
    # return make_response(jsonify(message='Failure')), 400
    print(type(config))
    config = json.loads(config)
    print(config)
    migration.run(config)

    return jsonify(
        message='success')
   # return redirect(url_for('success',name = user))

if __name__ == '__main__':
   app.run(debug = True)


# migration = Migration(source_config, target_config, migration_config)
# migration.schema()
# migration.run()
# migration.check()
