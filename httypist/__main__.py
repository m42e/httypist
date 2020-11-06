from . import server
from . import worker
import sys

def parse_args(args=None):
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    #parser.add_argument("square", type=int, help="display a square of a given number")
    #parser.add_argument("-v", "--verbosity", type=int, help="increase output verbosity")
    parser.add_argument("-w", "--worker", action='store_true', help="start worker")
    return parser.parse_known_args(args)

if __name__ == "__main__":
    args, unknown = parse_args()
    sys.argv = sys.argv[0:1] + unknown
    if args.worker:
        worker.main()
    else:
        server.main()
