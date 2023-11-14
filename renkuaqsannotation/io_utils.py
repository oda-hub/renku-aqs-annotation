import os

from git import Repo


def gitignore_file(*args):
    if os.path.exists('.gitignore'):
        with open('.gitignore') as gitignore_file_lines:
            lines = gitignore_file_lines.readlines()
        lines_to_add = []
        for file_name in args:
            if file_name + "\n" not in lines:
                lines.append(file_name + "\n")
                lines_to_add.append(file_name)

        if len(lines_to_add) > 0:
            commit_msg = ", ".join(lines_to_add) + " files added to the .gitignore file"
            with open(".gitignore", "w") as gitignore_file_write:
                gitignore_file_write.writelines(lines)
            repo = Repo('.')
            repo.index.add(".gitignore")
            repo.index.commit(commit_msg)
