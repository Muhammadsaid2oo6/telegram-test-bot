import json
import os
from datetime import datetime

# Data storage files
TESTS_FILE = "data/tests.json"
STUDENTS_FILE = "data/students.json"
OPEN_TESTS_FILE = "data/open_tests.json"

def load_json(file_path):
    """Load data from a JSON file."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(file_path, data):
    """Save data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def backup_data():
    """Create a backup of all database files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"data/backup_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files = [TESTS_FILE, STUDENTS_FILE, OPEN_TESTS_FILE]
    for file in files:
        if os.path.exists(file):
            data = load_json(file)
            backup_file = os.path.join(backup_dir, os.path.basename(file))
            save_json(backup_file, data)
    
    print(f"✅ Backup created in {backup_dir}")

def restore_data(backup_dir):
    """Restore data from a backup directory."""
    if not os.path.exists(backup_dir):
        print(f"❌ Backup directory {backup_dir} not found!")
        return
    
    files = [TESTS_FILE, STUDENTS_FILE, OPEN_TESTS_FILE]
    for file in files:
        backup_file = os.path.join(backup_dir, os.path.basename(file))
        if os.path.exists(backup_file):
            data = load_json(backup_file)
            save_json(file, data)
    
    print("✅ Data restored successfully!")

def view_data(file_type):
    """View data from a specific file."""
    file_map = {
        "students": STUDENTS_FILE,
        "tests": TESTS_FILE,
        "open_tests": OPEN_TESTS_FILE
    }
    
    if file_type not in file_map:
        print("❌ Invalid file type! Use: students, tests, or open_tests")
        return
    
    file_path = file_map[file_type]
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found!")
        return
    
    data = load_json(file_path)
    print(f"\n📊 {file_type.upper()} DATA:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    while True:
        print("\n📚 Database Management Menu:")
        print("1. Create backup")
        print("2. Restore from backup")
        print("3. View students data")
        print("4. View tests data")
        print("5. View open tests data")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ")
        
        if choice == "1":
            backup_data()
        elif choice == "2":
            backup_dir = input("Enter backup directory name (e.g., backup_20240320_123456): ")
            restore_data(f"data/{backup_dir}")
        elif choice == "3":
            view_data("students")
        elif choice == "4":
            view_data("tests")
        elif choice == "5":
            view_data("open_tests")
        elif choice == "6":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice! Please try again.")

if __name__ == "__main__":
    main() 