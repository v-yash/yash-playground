import os
import subprocess
import json
from datetime import datetime

# Configuration
SOURCE_HOST = ""
SOURCE_DB_USER = ""
SOURCE_DB_PASSWORD = ""

DATABASES=["db1", "db2"]

SCHEMA_NAME = "treebo_schema" 
DUMP_DIR = "/home/yash.verma/dumps/treebo_prod"
LOG_FILE = "/home/yash.verma/treebo_prod_dump_logs"

def load_migration_log():
    """Load migration status log."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_migration_log(log_data):
    """Save migration status log."""
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)

def migrate_database(db_name, migration_log):
    """Performs dump and restore for a specific schema within a database."""
    dump_file = os.path.join(DUMP_DIR, "{}_{}_dump.sql".format(db_name, SCHEMA_NAME))
    
    try:
        # Dump database with specific schema
        print("Dumping schema '{}' from database: {}".format(SCHEMA_NAME, db_name))
        dump_cmd = (
            "PGPASSWORD={} pg_dump -h {} -U {} -d {} -F c --schema={} -f {}".format(
                SOURCE_DB_PASSWORD, SOURCE_HOST, SOURCE_DB_USER, db_name, SCHEMA_NAME, dump_file
            )
        )
        subprocess.run(dump_cmd, shell=True, check=True)
        
        print("Schema '{}' from {} dumped successfully.".format(SCHEMA_NAME, db_name))
        migration_log[db_name] = {"status": "success", "timestamp": str(datetime.now())}
        save_migration_log(migration_log)
    
    except subprocess.CalledProcessError as e:
        print("Migration failed for {}: {}".format(db_name, e))
        migration_log[db_name] = {"status": "failed", "timestamp": str(datetime.now()), "error": str(e)}
        save_migration_log(migration_log)

def main():
    migration_log = load_migration_log()

    for db in DATABASES:
        if db in migration_log and migration_log[db]["status"] == "success":
            print("Skipping {}, already migrated successfully.".format(db))
            continue

        print("Starting migration for {}".format(db))
        migrate_database(db, migration_log)

if __name__ == "__main__":
    main()