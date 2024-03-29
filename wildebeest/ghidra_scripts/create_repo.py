#Create Repo
#@author Caleb Stewart
#@category phd
#@keybinding
#@menupath
#@toolbar

# this try/except construction makes intellisense nice with ghidra type stubs
# installed :)
# https://github.com/VDOO-Connected-Trust/ghidra-pyi-generator

import ghidra
try:
    from ghidra.ghidra_builtins import *
except:
    pass

from ghidra.base.project import GhidraProject
from ghidra.util.exception import DuplicateNameException

# Running from headless analyzer
# ------------------------------
# [analyzeHeadless <project_location> <project_name> ...]
# analyzeHeadless . empty -postScript create_repo.py <username> <password> <repo_name> -deleteProject -noanalysis

# parse args
usage = 'Usage: create_repo.py <repo_name> [<username> <password> [host:port]]'
args = getScriptArgs()
if len(args) < 1:
    print('Not enough arguments given!')
    print(usage)
    exit(0)

repo_name = args[0]
username = args[1] if len(args) > 1 else ''
password = args[2] if len(args) > 2 else ''
host, port = args[3].split(':') if len(args) > 3 else ('localhost', 13100)
port = int(port)

if username and password:
    print('Using username={}, password={}'.format(username, password))
    setServerCredentials(username, password)

# delete a file:
# https://github.com/NationalSecurityAgency/ghidra/issues/2180

def get_items_recursive(repo, folder):
    items = []
    for subfolder in repo.getSubfolderList(folder):
        items.extend(get_items_recursive(repo, subfolder))
        items.extend(repo.getItemList(folder))
    return items

def clear_repo(repo):
    for item in get_items_recursive(repo, '/'):
        repo.deleteItem(item.parentPath, item.name, item.version)

# NOTE: not using clear_repo yet, but it's here if I need it later

GhidraProject.getServerRepository(host, port, repo_name, True)
