#!/usr/bin/env python3
import argparse
import sys

# Add project root to sys.path so it can find instance folder
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from instance.config import SQLALCHEMY_DATABASE_URI
from sqlalchemy import create_engine, text


def execute_sql(sql, connect_string):
    engine = create_engine(connect_string, echo=False)
    with engine.connect() as connection:
        connection.execute(text(sql))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run sql from file')
    parser.add_argument('-f', '--filename', help='input sql file', required=False)
    parser.add_argument('-c', '--dbconnect', help='db connect string')
    args = parser.parse_args()
    if args.filename:
        with open(args.filename, 'r') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()
    sql = ''
    for line in lines:
        if not line.strip().startswith('--') and len(line.strip())>0:
            sql += line
    if args.dbconnect:
        connect_string = args.dbconnect
    else:
        connect_string =  SQLALCHEMY_DATABASE_URI
    execute_sql(sql, connect_string)



