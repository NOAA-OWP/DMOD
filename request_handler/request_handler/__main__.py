from . import RequestHandler
from socket import gethostname

# IMPORTANT: host must the hostname in the ssl cert, or connection will fail
#host = 'request-test'
host = gethostname()
port = '3012'


def main():
    # Init request handler on this machine, listening on port 3012
    handler = RequestHandler(host, port)
    handler.run()


if __name__ == '__main__':
    main()