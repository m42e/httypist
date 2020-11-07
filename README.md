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
- Simple mechanism for authentication


## Implementation

- Python fastapi http handler
- Ninja2 Template engine (for your templates)
- xelatex for the LaTeX processing (if you wish and need)
- rq for the background generation of documents
- docker container for easy deployment

## Issues to think about

- At the moment the update and the generation are not protected against each other, so generation may fail when an update is started at the same time which e.g. deletes the template.
- It is single user design at the moment. So you can configure only one repo as source for all the templates.
- The template source is restricted to folders. Templates in subfolders are not supported.
- It is an optimistic implementation


## Usage

### 1. Create a repository with templates

Create a git repository with templates you want to use. Each template requires:

- a own folder
- file(s) with the extension `.jinja`
- a config file `config.yml`

All files, with the ending `.jinja` will be processed as template. This means you can keep some structure for your documents. 
The template folder could have a separate file named `config.yml` which could set the options for the selection of this template and additional options passed to the processor.

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
access:
  - "sometokenyoucanchoose"
```
The `selector` selects the matching template based on the data provided. This enables to have a folder structure besides the selection mechanism and reuse templates.

The `filetypes` block is used to configure the jinja2 Environment. This is configurable per filetype.

In the `post` section you could define commands (with parameters) that should be run, after the template replacement took place.

The final `callback` does exactly what the name suggests, it performs a callback to the url (which is also a template and can use the data from the request). It could include data.

Under the `access` key you can list some strings which act as tokens required in the authentication header to generate the document.


### Docker

There are two docker containers, one is for the frontend, taking the requests, the other one is for the worker, actually doing the real work.
It is utilizing redis for the job and result. See the [docker-compose.yml](docker/docker-compose.yml) for details

You start the docker container with a set of environment variables, such as:

```
GIT_REPO=somehost:your/repo
```

This will clone the git repository containing the templates and configuration. There will also be an URL for updating the repository (`/update`), so webhooks for the repository work fine.

You add a folder to the repository, containing a file like this:

`test.jinja`
```
Hello {{ data['client']['name'] }}
```

