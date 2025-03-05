import os
import subprocess
import json
from datetime import datetime

# Configuration
SOURCE_HOST = "host"
SOURCE_DB_USER = "user"
SOURCE_DB_PASSWORD = "pwd"
TARGET_DB_USER = "user"
TARGET_DB_PASSWORD = "pwd"
TARGET_HOST = "host"
DATABASES = ["db1","db2"]
DUMP_DIR = "/data2t/dumps"  # Ensure this directory exists on your EC2 instance
LOG_FILE = "/data2t/logs"  # Log file to track progress

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
    """Performs dump, restore, and cleanup for a database."""
    dump_file = os.path.join(DUMP_DIR, "{}_stage_dump.sql".format(db_name))

    try:
        # Dump database
        print("Dumping database: {}".format(db_name))
        dump_cmd = "PGPASSWORD={} pg_dump -h {} -U {} -d {} -F c --exclude-table-data='awsdms_*' -f {}".format(
            SOURCE_DB_PASSWORD, SOURCE_HOST, SOURCE_DB_USER, db_name, dump_file
        )
        subprocess.run(dump_cmd, shell=True, check=True)

        # Restore database
        print("Restoring database: {}".format(db_name))
        restore_cmd = "PGPASSWORD='{}' pg_restore -h {} -U {} -d {} -F c {}".format(
            TARGET_DB_PASSWORD, TARGET_HOST, TARGET_DB_USER, db_name, dump_file
        )
        restore_process = subprocess.run(restore_cmd, shell=True)

        # Check return code but allow minor errors
        if restore_process.returncode != 0:
            print("Warning: Restore for {} encountered minor errors, but continuing.".format(db_name))
            migration_log[db_name] = {"status": "warning", "timestamp": str(datetime.now()), "error": "Restore completed with warnings"}
        else:
            print("Migration successful for {}.".format(db_name))
            migration_log[db_name] = {"status": "success", "timestamp": str(datetime.now())}

        save_migration_log(migration_log)

        # Cleanup dump file
        print("Cleaning up dump file: {}".format(dump_file))
        os.remove(dump_file)

    except subprocess.CalledProcessError as e:
        print("Migration failed for {}: {}".format(db_name, e))
        migration_log[db_name] = {"status": "failed", "timestamp": str(datetime.now()), "error": str(e)}
        save_migration_log(migration_log)

def main():
    migration_log = load_migration_log()

    for db in DATABASES:
        if db in migration_log and migration_log[db]["status"] in ["success", "warning"]:
            print("Skipping {}, already migrated successfully.".format(db))
            continue

        print("Starting migration for {}".format(db))
        migrate_database(db, migration_log)

if __name__ == "__main__":
    main()

