from pathlib import Path
import argparse

home_dir = Path.home()
base_directory = home_dir / 'Documents' / 'neural_amp_models' 

def do_rename(directory, prefix_text, dry_run=False):
    for file_path in directory.iterdir():
        if file_path.is_file():
            new_name = prefix_text + file_path.stem + file_path.suffix
            print(file_path.parent / new_name)
            if not dry_run:
                file_path.rename(file_path.parent / new_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog = 'rename NAM files',
                    description = 'Rename the NAM files in a directory to make more obvious')

    # Training mode selection
    parser.add_argument("--dir", help="directory withing NAM where files will be renamed")
    parser.add_argument("--prefix", help="prefix to add")
    parser.add_argument("-d", "--dry_run", action='store_true')

    args = parser.parse_args()

    directory = base_directory / args.dir 
    prefix = args.prefix

    do_rename(directory, prefix, args.dry_run)
    

