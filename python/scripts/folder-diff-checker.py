import os
import argparse

def get_files_in_folder(folder_path):
    """Returns a set of filenames in the given folder."""
    if not os.path.exists(folder_path):
        print(f"Warning: Folder '{folder_path}' does not exist.")
        return set()
    return set(os.listdir(folder_path))

def compare_folders(folder1, folder2):
    """Compares two folders and returns missing files in each."""
    files1 = get_files_in_folder(folder1)
    files2 = get_files_in_folder(folder2)
    
    missing_in_folder1 = files2 - files1
    missing_in_folder2 = files1 - files2
    
    return missing_in_folder1, missing_in_folder2

def main():
    parser = argparse.ArgumentParser(description="Compare two folders and find missing files.")
    parser.add_argument("folder1", help="Path to the first folder")
    parser.add_argument("folder2", help="Path to the second folder")
    args = parser.parse_args()
    
    missing_in_folder1, missing_in_folder2 = compare_folders(args.folder1, args.folder2)
    
    print("Missing files:")
    print(f"{args.folder1}: {', '.join(missing_in_folder1) if missing_in_folder1 else 'None'}")
    print(f"{args.folder2}: {', '.join(missing_in_folder2) if missing_in_folder2 else 'None'}")

if __name__ == "__main__":
    main()

# python3 folder-diff-checker.py path1 path2