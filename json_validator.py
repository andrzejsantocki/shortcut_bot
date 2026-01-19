
import json
import argparse

def validate_json(file_path):
    """
    Validates the syntax of a JSON file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        tuple: A tuple containing a boolean and a message.
               (True, "JSON is valid.") if the JSON is valid.
               (False, "Error message") if the JSON is invalid.
    """
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True, "JSON is valid."
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e.msg} at line {e.lineno} column {e.colno} (char {e.pos})"
    except FileNotFoundError:
        return False, f"File not found: {file_path}"
    except Exception as e:
        return False, f"An unexpected error occurred: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Validate JSON file syntax.')
    parser.add_argument('file_path', type=str, help='The path to the JSON file to validate.')
    args = parser.parse_args()

    is_valid, message = validate_json(args.file_path)
    print(is_valid)
    if not is_valid:
        print(message)
