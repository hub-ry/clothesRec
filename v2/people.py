"""Create private links: python3 v2/people.py add 'Name', or list."""
import argparse
import secrets

import db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('name')
    commands.add_parser('list')
    args = parser.parse_args()
    conn = db.connect()
    try:
        if args.command == 'add':
            if not args.name.strip():
                parser.error('Name must not be blank')
            token = secrets.token_urlsafe(16)
            conn.execute('INSERT INTO people (name, token, created_at) VALUES (?, ?, ?)',
                         (args.name, token, db.now()))
            conn.commit()
            print(f'/u/{token}')
        else:
            for person in conn.execute('SELECT name, token FROM people ORDER BY id'):
                print(f"{person['name']}\t/u/{person['token']}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
