import os

def merge_txt_files():
    # Path for the merged output file
    merged_file_path = "Trump-EO.txt"
   
    # Open the merged file in write mode
    with open(merged_file_path, "w") as merged_file:
        # Walk through the current directory and its subdirectories
        for root, _, files in os.walk("."):
            for file in files:
                if file.endswith(".txt") and file != "merged.txt":
                    # Construct full file path
                    txt_file_path = os.path.join(root, file)
                    
                    # Read and append content to the merged file
                    with open(txt_file_path, "r") as txt_file:
                        content = txt_file.read()
                        merged_file.write(f"--- {txt_file_path} ---\n")
                        merged_file.write(content + "\n\n")
                        print(f"Merged: {txt_file_path}")

if __name__ == "__main__":
    merge_txt_files()