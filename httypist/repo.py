import subprocess
import os
import os.path
import stat


def update(url=None, directory=None, token=None):
    if url is None:
        url = os.getenv("GIT_URL", False)
    if url == False:
        raise Exception("Git repository must have an url")

    if directory is None:
        directory = "repo"

    env = dict(os.environ)

    git_base_command = ["git"]

    if not os.path.exists(directory):
        subprocess.run(["git", "clone", "--depth", "1", url, directory], env=env)
    else:
        return
        subprocess.run(["git", "fetch"], cwd=directory)
        subprocess.run(
            ["git", "reset", "--hard", "origin/master"], cwd=directory, env=env
        )
