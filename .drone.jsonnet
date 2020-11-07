[
  {
    kind: 'pipeline',
    type: 'docker',
    name: 'docker-server',
    steps: [
      {
        name: 'build',
        image: 'plugins/docker',
        settings: {
          tags: ['latest', '${DRONE_COMMIT_SHA:0:8}'],
          dockerfile: 'docker/httypist/Dockerfile',
          registry: 'registry.d1v3.de',
          repo: 'registry.d1v3.de/httypist/server',
          config: { from_secret: 'dockerconfigjson' },
        },
      },
    ],
    trigger: { event: ['push'] },
  },
  {
    kind: 'pipeline',
    type: 'docker',
    name: 'docker-processor',
    steps: [
      {
        name: 'build',
        image: 'plugins/docker',
        settings: {
          tags: ['latest', '${DRONE_COMMIT_SHA:0:8}'],
          dockerfile: 'docker/httypist-processor/Dockerfile',
          registry: 'registry.d1v3.de',
          repo: 'registry.d1v3.de/httypist/processor',
          config: { from_secret: 'dockerconfigjson' },
        },
      },
    ],
    trigger: { event: ['push'] },
  },
]
