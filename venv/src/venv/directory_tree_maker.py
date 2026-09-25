import os
import json

def directory_search(path, saved_file_paths):
    for next_file in os.listdir(path):
        next_path = path + '/' + next_file
        if os.path.isdir(next_path):
            saved_file_paths = directory_search(next_path, saved_file_paths)
        else:
            saved_file_paths.append(next_path)
            
    return saved_file_paths

def push_new_file(old_path, new_path):
    folders = new_path.split('/')
    currect_path = folders[0]
    for next_folder in folders[1:]:
        if not os.path.exists(currect_path):
            os.makedirs(currect_path)
        currect_path += '/' + next_folder
    os.replace(old_path, new_path)

def clear(path):
    for next_file in os.listdir(path):
        next_path = path + '/' + next_file
        if os.path.isdir(next_path):
            saved_file_paths = clear(next_path)
            if len(os.listdir(path)) == 0:
                os.rmdir(next_path)
                
def directory_tree_maker_manager(main_root, new_paths, programm_path):
    saved_file_paths = []
    saved_file_paths = directory_search(main_root, [])
    
    data = {}
    data["saved_file_paths"] = saved_file_paths
    with open(programm_path + "/saved_paths.json", "w") as f:
        json.dump(data, f)
    
    for paths_pair in new_paths:
        push_new_file(paths_pair[0], paths_pair[1])

    clear(main_root)
    
#def rollback(programm_path):
    

directory_tree_maker_manager("C:/Users/MSI/Downloads/gg2", [["C:/Users/MSI/Downloads/gg2/vf.txt", "C:/Users/MSI/Downloads/gg2/new/vf.txt"]], "C:/Users/MSI/Downloads/project_shlak")