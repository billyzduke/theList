import macos_tags

# https://github.com/dmkskn/macos-tags/issues/9
print(macos_tags.get_all('tags.py'))

# [Tag(name='Unfit AMF', color=<Color.RED: 6>), Tag(name='Good 2 Go Girl!', color=<Color.GREEN: 2>), Tag(name='Orange', color=<Color.ORANGE: 7>), Tag(name='Purple', color=<Color.PURPLE: 3>), Tag(name='Red', color=<Color.RED: 6>), Tag(name='Blue', color=<Color.BLUE: 4>), Tag(name='Gray', color=<Color.GRAY: 1>), Tag(name='Yellow', color=<Color.YELLOW: 5>)]

# # Path to the file
# file_path = "/path/to/your/file.txt"

# # Tags to add
# tags_to_add = ["Important", "Work"]

# # Add tags to the file
# macos_tags.settags(file_path, tags_to_add)

# # Verify the tags
# current_tags = gettags(file_path)
# print(f"Current tags for {file_path}: {current_tags}")
# Adding Tags with Colors
# If you want to add tags with specific colors, you can use the Tag data class and Color enumeration provided by the library:

# Python

# Copy code
# from macos_tags import settags, Tag, Color

# # Path to the file
# file_path = "/path/to/your/file.txt"

# # Create tags with colors
# colored_tags = [
#     Tag("Urgent", Color.RED),
#     Tag("Review", Color.BLUE)
# ]

# # Add colored tags to the file
# settags(file_path, colored_tags)
# Notes
# Ensure the file path is correct and accessible.
# Tags added will be visible in Finder under the "Tags" section.
# This approach is efficient and integrates seamlessly with macOS's tagging system. Let me know if you need further assistance!


