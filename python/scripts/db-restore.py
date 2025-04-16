import os
import subprocess
import json
from datetime import datetime

TARGET_HOST = ""
TARGET_DB_USER = ""
TARGET_DB_PASSWORD = ""

DUMP_DIR = "/home/yash.verma/dumps/"
LOG_FILE = "/home/yash.verma/logs.json"

DATABASES = ["db1", "db2"]

SCHEMA_NAME = "schema" 

def load_restore_log():
    """Load restore status log."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_restore_log(log_data):
    """Save restore status log."""
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)

def restore_database(db_name, restore_log):
    """Restores a specific schema from dump file into the target database."""
    dump_file = os.path.join(DUMP_DIR, f"{db_name}_treebo_schema_dump.sql")

    if not os.path.exists(dump_file):
        print(f"Dump file {dump_file} not found. Skipping restore for {db_name}.")
        return

    try:
        print(f"Restoring schema '{SCHEMA_NAME}' to database: {db_name}")
        restore_cmd = (
            f"PGPASSWORD={TARGET_DB_PASSWORD} pg_restore -h {TARGET_HOST} -U {TARGET_DB_USER} "
            f"-d {db_name} --schema={SCHEMA_NAME} -c {dump_file}"
        )
        subprocess.run(restore_cmd, shell=True, check=True)
        
        print(f"Schema '{SCHEMA_NAME}' restored successfully to {db_name}.")
        restore_log[db_name] = {"status": "success", "timestamp": str(datetime.now())}
        save_restore_log(restore_log)

    except subprocess.CalledProcessError as e:
        print(f"Restore failed for {db_name}: {e}")
        restore_log[db_name] = {"status": "failed", "timestamp": str(datetime.now()), "error": str(e)}
        save_restore_log(restore_log)

def main():
    restore_log = load_restore_log()

    for db in DATABASES:
        if db in restore_log and restore_log[db]["status"] == "success":
            print(f"Skipping {db}, already restored successfully.")
            continue

        print(f"Starting restore for {db}")
        restore_database(db, restore_log)

if __name__ == "__main__":
    main()
