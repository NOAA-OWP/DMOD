#!/bin/bash

name='request-test'

openssl req -newkey rsa:2048 -nodes -keyout privkey.pem -x509 -days 36500 -out certificate.pem -subj "/C=US/ST=Alabama/L=Tuscaloosa/O=OWP/OU=APD/CN=$name/emailAddress=nels.frazier@noaa.gov"
