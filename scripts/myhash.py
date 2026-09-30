#!/usr/bin/env python3

from Crypto.Hash import MD4
import binascii
import getpass

PASSWORD=getpass.getpass("password: ")
password_hash = MD4.new(PASSWORD.encode('utf-16le')).hexdigest()
print(str(password_hash))
print('{}:{}'.format('0'*32, password_hash))
