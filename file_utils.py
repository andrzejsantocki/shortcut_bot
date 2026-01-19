def get_line_count(file_path):
    """Gets the number of lines in a file."""
    try:
        with open(file_path, 'r') as f:
            return len(f.readlines())
    except FileNotFoundError:
        return 0

def update_shortcuts_safely(file_path, updated_content):
    """
    Safely updates the shortcuts file after checking the line count.
    Returns True on success, False on failure.
    """
    before_lines = get_line_count(file_path)
    after_lines = len(updated_content.splitlines())

    if after_lines < before_lines:
        print("Error: Update would result in a smaller file. Aborting.")
        return False

    with open(file_path, 'w') as f:
        f.write(updated_content)
    return True