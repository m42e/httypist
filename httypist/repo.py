import subprocess
import os
import os.path
import stat


def update(url=None, directory=None, pubkey=None):
    if url is None:
        url = os.getenv("GIT_URL", False)
    if url == False:
        raise Exception("Git repository must have an url")

    if pubkey is None:
        pubkey = os.getenv("GIT_SSH_KEY", None)
    if pubkey is not None:
        if not os.path.isfile("ssh_key_for_repo"):
            with open("ssh_key_for_repo", "w") as f:
                f.write(pubkey)
                f.write("\n")
            os.chmod("ssh_key_for_repo", stat.S_IRUSR | stat.S_IWUSR)

    if directory is None:
        directory = "repo"

    env = dict(os.environ)

    git_base_command = ["git"]
    if pubkey is not None:
        pwd = os.getcwd()
        keyfile = os.path.join(pwd, "ssh_key_for_repo")
        env["GIT_SSH_COMMAND"] = f"ssh -i {keyfile}"

    if not os.path.exists(directory):
        subprocess.run(["git", "clone", "--depth", "1", url, directory], env=env)
    else:
        return
        subprocess.run(["git", "fetch"], cwd=directory)
        subprocess.run(
            ["git", "reset", "--hard", "origin/master"], cwd=directory, env=env
        )
