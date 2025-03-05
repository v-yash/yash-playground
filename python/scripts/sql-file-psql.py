import os
import subprocess
import psycopg2

# Database connection details
HOST = "host"
USERNAME = "user"
PASSWORD = "pwd"
SQL_FILES_DIR = "/dir"  # Directory where .sql files are stored

def execute_sql_file(db_name):
    sql_file = os.path.join(SQL_FILES_DIR, "{}.sql".format(db_name))
    if not os.path.exists(sql_file):
        print("SQL file not found for database: {}".format(db_name))
        return
    
    try:
        print("Executing {} on {}...".format(sql_file, db_name))
        command = "PGPASSWORD={} psql -h {} -U {} -d {} -f {}".format(PASSWORD, HOST, USERNAME, db_name, sql_file)
        subprocess.run(command, shell=True, check=True)
        print("Execution completed for {}".format(db_name))
    except subprocess.CalledProcessError as e:
        print("Error executing {} on {}: {}".format(sql_file, db_name, e))


def check_db_connection(db_name):
    try:
        conn = psycopg2.connect(host=HOST, dbname=db_name, user=USERNAME, password=PASSWORD)
        conn.close()
        return True
    except psycopg2.Error as e:
        print("Connection failed for {}: {}".format(db_name, e))
        return False


def main():
    db_list = ["db1","db2"]

    for db_name in db_list:
        if check_db_connection(db_name):
            execute_sql_file(db_name)
        else:
            print("Skipping {} due to connection failure.".format(db_name))

if __name__ == "__main__":
    main()
