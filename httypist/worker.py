#!/usr/bin/env python
import sys
from rq import Connection, Worker
from rq import Queue
from redis import Redis

# Preload libraries
from . import processor


redis_conn = Redis(host="localhost")

def main():
    # Provide queue names to listen to as arguments to this script,
    # similar to rq worker
    with Connection():
        qs = sys.argv[1:] or ['process']

        w = Worker(qs)
        w.work(with_scheduler=True)

if __name__ == '__main__':
    main()
