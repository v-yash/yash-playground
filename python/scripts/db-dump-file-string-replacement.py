import os

# Configuration
dump_directory = "/home/yash.verma/dumps/"
old_string = b"schema1"
new_string = b"schema2"

def replace_in_file(file_path, old, new):
    """Replace occurrences of a string in a binary file."""
    with open(file_path, "rb") as file:  # Read in binary mode
        content = file.read()

    # Replace only if the old string is found
    if old in content:
        content = content.replace(old, new)
        with open(file_path, "wb") as file:  # Write back in binary mode
            file.write(content)
        print(f"Updated: {file_path}")
    else:
        print(f"No changes needed: {file_path}")

def process_dump_files(directory):
    """Iterate over SQL files in the directory and perform replacement."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".sql"):
                file_path = os.path.join(root, file)
                replace_in_file(file_path, old_string, new_string)

if __name__ == "__main__":
    process_dump_files(dump_directory)


# sed -i 's/Schema: ten100_schema;/Schema: public;/g' ten100_schema_dump.sql
# sed -i 's/ten100_schema./public./g' ten100_schema_dump.sql

