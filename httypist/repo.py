import subprocess
import os
import os.path
import stat
import logging

_logger = logging.getLogger(__name__)


def update(url=None, directory=None, token=None):
    if url is None:
        url = os.getenv("GIT_URL", False)
        _logger.debug(f"No url set using Environment: {url}")
    if url == False:
        _logger.debug(f"Neither url nor GIT_URL found")
        return 

    if directory is None:
        _logger.debug(f"Using default directory")
        directory = "repo"

    env = dict(os.environ)

    git_base_command = ["git"]

    if not os.path.exists(directory):
        _logger.debug(f"Clone repository to {directory}")
        subprocess.run(["git", "clone", "--depth", "1", url, directory], env=env)
    else:
        _logger.debug(f"Update Repository")
        subprocess.run(["git", "fetch"], cwd=directory, env=env)
        subprocess.run(
            ["git", "reset", "--hard", "origin/master"], cwd=directory, env=env
        )
