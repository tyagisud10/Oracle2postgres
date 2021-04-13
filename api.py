from flask import Flask,request

import run_migration
app = Flask(__name__)



#@app.route('/submit')

# def call_func():
#     schema_list = request.args.get('schema_list')
#     username = request.args.get('username')
#     host = request.args.get('host')
#     port = request.args.get('port')
#     database = request.args.get('database')
#     password = request.args.get('password')
#
#     return run_migration.main()
# allow both GET and POST requests
@app.route('/form-example', methods=['GET', 'POST'])
def form_example():
    # handle the POST request
    if request.method == 'POST':
        Schema_list = request.form.get('Schema_list')
        username = request.form.get('username')
        host = request.form.get('host')
        port = request.form.get('port')
        database = request.form.get('database')
        password = request.form.get('password')
        return '''
                  <h1>Source Details <h1>
                  <h4>The Schema_list value is: {}</h4>
                  <h4>The username value is: {}</h4>
                  <h4>The host value is: {}</h4>
                  <h4>The port value is: {}</h4>
                  <h4>The database value is: {}</h4>
                  <h4>The password value is: {}</h4>'''.format(Schema_list, username, host, port,database,password )

    # otherwise handle the GET request
    return '''
           <form method="POST">
               <h3>Source Details </h3>
               <div><label>Schema_list: <input type="text" name="Schema_list"></label></div>
               <div><label>username: <input type="text" name="username"></label></div>
               <div><label>host: <input type="text" name="host"></label></div>
               <div><label>port: <input type="text" name="port"></label></div>
               <div><label>database: <input type="text" name="database"></label></div>
               <div><label>password: <input type="text" name="password"></label></div>
               
               <h3>Target Details </h3>
               <div><label>username: <input type="text" name="username"></label></div>
               <div><label>host: <input type="text" name="host"></label></div>
               <div><label>port: <input type="text" name="port"></label></div>
               <div><label>database: <input type="text" name="database"></label></div>
               <div><label>password: <input type="text" name="password"></label></div>
               
               <h3>Load Details </h3>
               <div><label>Batch Size: <input type="text" name="batchsize"></label></div>
               <div><label>Load Type: <input type="text" name="loadtype"></label></div>
               <div><label>Trail Run: <input type="text" name="trialrun"></label></div>

               <input type="submit" value="Submit">
           </form>'''


if __name__ == '__main__':
    app.run(debug=True)