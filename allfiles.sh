#!/bin/bash

# Define the output file (will be created in the same directory as the script)
output_file="$(dirname "$0")/output.txt"

# Clear the output file if it already exists
> "$output_file"

# Traverse through all .py, .css, and .html files in the current directory and its subdirectories,
# excluding the a2a_reporting_dev directory.
find . -path ./a2a_reporting_dev -prune -o -type f \( -name '*.py' -o -name '*.css' -o -name '*.html' \) -print | while read -r file; do
    # Write the filename to the output file
    echo "Filename: $file" >> "$output_file"

    # Write the content of the file to the output file
    cat "$file" >> "$output_file"

    # Add a separator for readability (optional)
    echo -e "\n--- End of $file ---\n" >> "$output_file"
done

echo "Contents of all .py, .css, and .html files (excluding a2a_reporting_dev) written to $output_file"
