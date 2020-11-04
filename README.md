# Document automation

This is actually getting useful.

## Use of this

It is a http typist so a httypist. It should generate document for you in a known environment (docker container) and could be triggered via http. And the configuration and templates should be in a git repository.

## Targets

- HTTP Hooks a triggers
- HTTP Callbacks for the result 
- GIT Repository with the templates
- Template selection by 
  - url or 
  - data in the request
- PDF output using latex (you have to use a docker image as base for the worker, which has latex installed)
- Use template folders, including all the auxiliary files for the template
- No need to update the docker containers in case of a template update


## Implementation

- Python flask http handler
- Ninja2 Template engine
- xelatex for the LaTeX processing (if you wish and need)
- celery Offloading the load from the frontend
- docker container for easy deployment


## Templates

The templates are stored in a git repository.
Each template has to be in a separate folder. All files, with the ending `.ninja` will be processed as template. This means you can keep some structure for your documents. 
The template folder could have a separate file named `config.yml` which could set the options for the selection of this template and additional options passed to the processor

### config.yml

This is an example file:

```
selector:
  - json.custom_text_value1 == "ThisFile" 
filetypes:
  tex:
    jinja:
      block_start_string: '\BLOCK{'
      block_end_string: '}'
      variable_start_string: '\VAR{'
      variable_end_string: '}'
      comment_start_string: '\#{'
      comment_end_string: '}'
      line_statement_prefix: '%%'
      line_comment_prefix: '%#'
post:
  xelatex:
    - latexmk
    - -pdf
    - -pdflatex=xelatex -no-shell-escape -halt-on-error -interaction=batchmode %O %S
callback:
  method: post
  template: https://testapi.d1v3.de/index.php?test=hallo&hallo={{ args['wer'] }}
  data: 
    - name: vertrag.pdf
      binary: true
```
The `selector` selects the matching template based on the data provided. This enables to have a folder structure besides the selection mechanism and reuse templates.

The `filetypes` block is used to configure the jinja2 Environment. This is configurable per filetype.

In the `post` section you could define commands (with parameters) that should be run, after the template replacement took place.

The final `callback` does exactly what the name suggests, it performs a callback to the url (which is also a template and can use the data from the request). It could include data.


## Workflow

You start the docker container with a set of environment variables, such as:

```
GIT_REPO=somehost:your/repo
GIT_USERNAME=username
REDIS_URL=redis://localhost
```

This will clone the git repository containing the templates and configuration. There will also be an url for updating the repository, so webhooks for the repository work fine.

You add a folder to the repository, containing a file like this:

```
Hello {{ data['client']['name'] }}
```

