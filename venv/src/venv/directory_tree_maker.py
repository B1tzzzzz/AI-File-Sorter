import os
import json

def directory_search(path, saved_file_paths): #Обход директории для сохранения путей
    for next_file in os.listdir(path):
        next_path = path + '/' + next_file
        if os.path.isdir(next_path):
            saved_file_paths = directory_search(next_path, saved_file_paths)
        else:
            saved_file_paths.append(next_path)
            
    return saved_file_paths

def push_new_file(old_path, new_path): #Перемещение файла + создание новых папок
    folders = new_path.split('/')
    currect_path = folders[0]
    for next_folder in folders[1:]:
        if not os.path.exists(currect_path):
            os.makedirs(currect_path)
        currect_path += '/' + next_folder
    os.replace(old_path, new_path)

def move_files_into_root(main_root, path): #Перемещение всех файлов в корень
    for next_file in os.listdir(path):
        next_path = path + '/' + next_file
        if os.path.isdir(next_path):
            move_files_into_root(main_root, next_path)
        else:
            os.replace(next_path, main_root + '/' + next_file)

def clear(path): #Удаление пустых папок
    for next_file in os.listdir(path):
        next_path = path + '/' + next_file
        if os.path.isdir(next_path):
            clear(next_path)
    if len(os.listdir(path)) == 0:
        os.rmdir(path)
                
def directory_tree_maker_manager(main_root, new_paths, programm_path): #main_root - строка, new_paths - список пар, programm_path - строка
    saved_file_paths = []
    saved_file_paths = directory_search(main_root, [])
    
    data = {}
    data["saved_file_paths"] = saved_file_paths
    with open(programm_path + "/saved_paths.json", "w") as json_data:
        json.dump(data, json_data)
    json_data.close()
    
    for paths_pair in new_paths:
        if os.path.exists(paths_pair[0]):
            push_new_file(paths_pair[0], paths_pair[1])

    clear(main_root)
    
def rollback(main_root, programm_path): #откат
    with open(programm_path + "/saved_paths.json", "r") as json_data:
        data = json.load(json_data)
    json_data.close()
    saved_file_paths = data["saved_file_paths"]
    
    move_files_into_root(main_root, main_root)
    
    for path in saved_file_paths:
        if os.path.exists(main_root + '/' + path.split('/')[-1]):
            push_new_file(main_root + '/' + path.split('/')[-1], path)
    
    clear(main_root)
    
#directory_tree_maker_manager("C:/Users/MSI/Downloads/gg2", [["C:/Users/MSI/Downloads/gg2/vf.txt", "C:/Users/MSI/Downloads/gg2/new/vf.txt"]], "C:/Users/MSI/Downloads/project_shlak")
#rollback("C:/Users/MSI/Downloads/gg2", "C:/Users/MSI/Downloads/project_shlak")