import psycopg2
import json

RDS_HOST = "host"
DB_USER = "user"
DB_PASSWORD = "host"
DATABASES = [
    "ar-module", "auth", "authz", "company-profiles", "crs",
    "finance-erp", "material-manager", "ups"
]
db_list=["catalog", "growth-realization", "hawkeye","interface-exchange", 
            "rackrate", "staff-management", "taxation"]
            
SCHEMA_NAME = "ten100_schema"

# Function to truncate all tables in the schema
def truncate_schema(db_name):
    try:
        conn = psycopg2.connect(
            dbname=db_name, user=DB_USER, password=DB_PASSWORD, host=RDS_HOST
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Fetch all tables in the schema
        cur.execute(
            f"""
            SELECT tablename FROM pg_tables
            WHERE schemaname = '{SCHEMA_NAME}';
            """
        )
        tables = cur.fetchall()
        
        if not tables:
            print(f"No tables found in {SCHEMA_NAME} schema of {db_name}")
            return
        
        print(f"Truncating tables in {SCHEMA_NAME} schema of {db_name}...")
        
        # Disable foreign key constraints temporarily
        cur.execute("SET session_replication_role = 'replica';")
        
        # Truncate all tables in the schema
        for table in tables:
            table_name = table[0]
            cur.execute(f'TRUNCATE TABLE {SCHEMA_NAME}.{table_name} CASCADE;')
            print(f"Truncated {SCHEMA_NAME}.{table_name} in {db_name}")
        
        # Re-enable foreign key constraints
        cur.execute("SET session_replication_role = 'origin';")
        
        cur.close()
        conn.close()
        print(f"Truncation completed for {db_name}")
    except Exception as e:
        print(f"Error truncating {SCHEMA_NAME} schema in {db_name}: {e}")

# Main execution
if __name__ == "__main__":
    for db in DATABASES:
        truncate_schema(db)
