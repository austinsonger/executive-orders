import os
import shutil

def convert_md_to_txt():
    # Walk through the current directory and its subdirectories
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".md"):
                # Construct full file paths
                md_file_path = os.path.join(root, file)
                txt_file_path = os.path.join(root, file.replace(".md", ".txt"))
                
                # Copy content from .md to .txt
                shutil.copyfile(md_file_path, txt_file_path)
                print(f"Copied: {md_file_path} -> {txt_file_path}")

if __name__ == "__main__":
    convert_md_to_txt()