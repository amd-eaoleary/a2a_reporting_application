from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from sqlalchemy.sql import text
import csv
import io
from flask import Response
from datetime import datetime
import configparser

app = Flask(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

username = config.get('DatabaseCredentials', 'username')
password = config.get('DatabaseCredentials', 'password')
host = config.get('DatabaseCredentials', 'host')
port = config.get('DatabaseCredentials', 'port')
database = config.get('DatabaseCredentials', 'database')

encoded_password = quote(password)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{username}:{encoded_password}@{host}:{port}/{database}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.route("/") 
def index(): 
    return render_template('home.html')

@app.route('/view_execution_history', methods=['GET'])
def view_execution_history():
    search_process = request.args.get('search_process', default='', type=str)
    status_filter = request.args.get('status_filter', default='', type=str)
    date_start = request.args.get('date_start', default=None, type=str)
    date_end = request.args.get('date_end', default=None, type=str)
    page = request.args.get('page', default=1, type=int)

    items_per_page = 100
    parameters = {}
    
    # Start building the SQL query
    query = 'SELECT * FROM "A2AMON"."A2A_EXECUTION_HISTORY" WHERE 1=1'

    if search_process:
        # Split the input on commas and prepare a condition
        process_names = [name.strip().lower() for name in search_process.split(',')]
        query += " AND lower(process_name) IN :process_names"
        parameters['process_names'] = tuple(process_names)

    if status_filter:
        query += " AND execution_status = :status_filter"
        parameters['status_filter'] = status_filter

    if date_start:
        query += " AND execution_start >= :date_start"
        parameters['date_start'] = date_start

    if date_end:
        query += " AND execution_start <= :date_end"
        parameters['date_end'] = date_end

    # Add LIMIT and OFFSET for pagination
    query += " ORDER BY execution_start DESC LIMIT :limit OFFSET :offset"
    parameters['limit'] = items_per_page
    parameters['offset'] = (page - 1) * items_per_page

    # Debug log for the query and parameters
    print("Executing SQL Query:", query)
    print("With Parameters:", parameters)

    # Execute the query
    with db.engine.connect() as connection:
        result = connection.execute(text(query), parameters)
        
        # Convert each row to a dictionary using mappings()
        all_execution_records = [dict(row) for row in result.mappings()]

    # Calculate the total number of records (for pagination)
    count_query = 'SELECT COUNT(*) FROM "A2AMON"."A2A_EXECUTION_HISTORY" WHERE 1=1'
    count_parameters = {}

    if search_process:
        count_query += " AND lower(process_name) IN :process_names"
        count_parameters['process_names'] = tuple(process_names)

    if status_filter:
        count_query += " AND execution_status = :status_filter"
        count_parameters['status_filter'] = status_filter

    if date_start:
        count_query += " AND execution_start >= :date_start"
        count_parameters['date_start'] = date_start

    if date_end:
        count_query += " AND execution_start <= :date_end"
        count_parameters['date_end'] = date_end

    with db.engine.connect() as connection:
        count_result = connection.execute(text(count_query), count_parameters)
        total_records = count_result.scalar()  # Get the count from the result

    total_pages = (total_records + items_per_page - 1) // items_per_page  # Calculate total pages

    return render_template('execution_history.html', records=all_execution_records, page=page, total_pages=total_pages)

@app.route('/view_integration_content', methods=['GET'])
def view_integration_content():
    page = request.args.get('page', default=1, type=int)
    items_per_page = 100
    offset = (page - 1) * items_per_page

    # SQL to fetch paginated data
    query = text('SELECT * FROM "A2AMON"."A2A_IFLOW_DATA" LIMIT :limit OFFSET :offset')
    count_query = 'SELECT COUNT(*) FROM "A2AMON"."A2A_IFLOW_DATA"'

    with db.engine.connect() as connection:
        # Fetch paginated IFLOW data
        result = connection.execute(query, {'limit': items_per_page, 'offset': offset})
        iflow_data = []
        
        for row in result:
            record = {
                'id': row[0],
                'version': row[1],
                'package_id': row[2],
                'name': row[3],
                'description': row[4],
                'created_by': row[5],
                'created_at': row[6],
                'modified_by': row[7],
                'modified_at': row[8]
            }
            iflow_data.append(record)

        # Fetch total record count without pagination
        count_result = connection.execute(text(count_query))
        total_records = count_result.scalar()  # Get the count from the result

    # Calculate total pages
    total_pages = (total_records + items_per_page - 1) // items_per_page

    return render_template('iflow_data.html', records=iflow_data, page=page, total_pages=total_pages)


@app.route('/download_csv', methods=['GET'])
def download_csv():
    search_process = request.args.get('search_process', default='', type=str)
    status_filter = request.args.get('status_filter', default='', type=str)
    date_start = request.args.get('date_start', default=None, type=str)
    date_end = request.args.get('date_end', default=None, type=str)

    parameters = {}
    query = 'SELECT * FROM "A2AMON"."A2A_EXECUTION_HISTORY" WHERE 1=1'

    if search_process:
        process_names = [name.strip().lower() for name in search_process.split(',')]
        query += " AND lower(process_name) IN :process_names"
        parameters['process_names'] = tuple(process_names)

    if status_filter:
        query += " AND execution_status = :status_filter"
        parameters['status_filter'] = status_filter

    if date_start:
        query += " AND execution_start >= :date_start"
        parameters['date_start'] = date_start

    if date_end:
        query += " AND execution_start <= :date_end"
        parameters['date_end'] = date_end

    query += " ORDER BY execution_start DESC"

    with db.engine.connect() as connection:
        result = connection.execute(text(query), parameters)
        records = [dict(row) for row in result.mappings()]

    # Create a CSV response
    def generate_csv():
        # Generate CSV from records
        output = csv.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        yield output.getvalue()

    return Response(generate_csv(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=execution_history.csv"})

# if __name__ == '__main__':
#     app.run(debug=True,host="0.0.0.0",port=5000)

if __name__ == '__main__':
    app.run(ssl_context=('cert.pem', 'key.pem'))