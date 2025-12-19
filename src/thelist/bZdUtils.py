import inspect

def line_info():
    # Get the current frame
    frame = inspect.currentframe()
    # Get the caller's frame info
    caller_frame = inspect.getframeinfo(frame.f_back)
    
    print(f"File: {caller_frame.filename}, Line: {caller_frame.lineno}", "\n")

# Convert string to integer safely in Python
def safe_str_to_int(s):
    """
    Converts a string to an integer with error handling.
    Returns the integer if successful, or None if conversion fails.
    """
    try:
        # Strip whitespace and convert
        return int(str(s).strip())
    except ValueError:
        print(f"Error: '{s}' is not a valid integer.")
        return None

def remove_value_from_list(arr, value):
    """
    Removes all occurrences of 'value' from the list 'arr'.
    Returns the updated list.
    """
    if not isinstance(arr, list):
        #raise TypeError("arr must be a list")
        return arr

    # Check if value exists
    if value not in arr:
        #print(f"Value '{value}' not found in list.")
        return arr

    # Remove all occurrences
    arr = [item for item in arr if item != value]
    #print(f"Value '{value}' removed successfully.")
    return arr
