import os

from git import Repo


def gitignore_file(file_name):
    if os.path.exists('.gitignore'):
        with open('.gitignore') as gitignore_file_lines:
            lines = gitignore_file_lines.readlines()
        if file_name + "\n" not in lines:
            lines.append(file_name + "\n")
            with open(".gitignore", "w") as gitignore_file_write:
                gitignore_file_write.writelines(lines)
            commit_msg = f"{file_name} added to the .gitignore file"
            repo = Repo('.')
            repo.index.add(".gitignore")
            repo.index.commit(commit_msg)
