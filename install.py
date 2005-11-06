
import os

install_path = os.curdir
bin_path = os.curdir
dirs_to_install = []
files_to_install = []
exclude_dirs = ['CVS','NSIS']
exclude_files = ['install.py','urk.desktop']

def identify_files():
    #set files to a list of the files we want to install
    for dirpath, dirnames, filenames in os.walk(os.curdir,topdown=True):
        dirnames[:] = [x for x in dirnames if x not in exclude_dirs]
        dirpath = os.path.split
        for filename in filenames:
            if filename not in exclude_files:
                filename = os.path.join(dirpath,filename)
                print "Marking file %s for installation" % filename
                files_to_install.append(filename)
        for dirname in dirnames:
            dirname = os.path.join(dirpath,dirname)
            print "Marking directory %s for installation" % dirname
            dirs_to_install.append(dirname)

def install_files():
    #move .py files to the destination directory
    pass
