
import os

install_path = os.curdir
bin_path = os.curdir
dirs_to_install = []
files_to_install = []
exclude_dirs = ['CVS','NSIS']
exclude_files = ['install.py','urk.desktop']

def identify_files(path=os.curdir, prefix=''):
    #set files to a list of the files we want to install
    for filename in os.listdir(path):
        abs_file = os.path.join(path,filename)
        rel_file = os.path.join(prefix,filename)
        if os.path.isfile(abs_file) and filename not in exclude_files:
            print "Marking file %s for installation" % rel_file
            files_to_install.append(rel_file)
        elif os.path.isdir(abs_file) and filename not in exclude_dirs:
            print "Marking directory %s for installation" % rel_file
            dirs_to_install.append(rel_file)
            identify_files(abs_file, rel_file)

def install_files():
    #move .py files to the destination directory
    pass
