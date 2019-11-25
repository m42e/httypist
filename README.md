# Document automation

This is still WIP

## Targets

- HTTP Callbacks, 
- GIT Repository with the templates
- Template selection by either url or element in the request
- PDF output using latex
- Use template folders, including all the auxiliary files for the template


## Implementierung

- Python flask http handler
- Ninja2 Template engine
- xelatex 
- all runs in docker containers


## Templates

The templates are stored in a git repository.
Each template has to be in a separate folder. All files, with the ending `.ninja` will be processed for the selected template.
The template folder could have a separate file named `config.yml` which could set the options for the selection of this template and additional options passed to the processor


## Workflow

You start the docker container with a set of environment variables, such as:

```
GIT_REPO=somehost:your/repo
GIT_USERNAME=username
GIT_SSH_KEY=ssh-rsa..........
REDIS_URL=redis://localhost
```

This will clone the git repository containing the templates and configuration. There will also be an url for updating the repository, so webhooks for the repository work fine.

You add a folder to the repository, containing a file like this:

```
Hello {{ data['client']['name'] }}
```
