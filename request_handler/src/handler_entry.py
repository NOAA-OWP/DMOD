#!/usr/bin/env python3
"""
Entry script for request handler service
"""
from RequestHandler import RequestHandler

# IMPORTANT: host must the hostname in the ssl cert, or connection will fail
host = 'request-test'
port = '3012'

def main():
    #Init request handler on this machine, listening on port 3012

    handler = RequestHandler(host, port)
    handler.run()

if __name__ == '__main__':
    main()
