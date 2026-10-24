"""Run with python3 v2/server.py. HOST=127.0.0.1 PORT=8090 by default.

Start: python3 v2/collect.py --max-pages 1
       python3 v2/people.py add "Name"
       python3 v2/server.py
Checks: python3 -m unittest v2/test_v2.py

CLOTHESREC_DB defaults to data/clothesrec.db, relative to the repo root.
Keep private links private: anyone holding a link can read and change that
person's feedback. Use HTTPS when exposing this server beyond localhost.
Collection never removes old inventory; consult each item's last-check time.
Unknown currency and availability stay unknown. Summaries require three ratings.
DEEPSEEK_API_KEY stays server-side; only the explicit summary action sends data.
Calls are limited to one per person per minute and 30 total per rolling day.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, unquote, urlsplit

import db
import summarize

STATIC = Path(__file__).resolve().parent / 'static'
REACTIONS = ('dislike', 'like', 'love')


class HTTPError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        # Never print bearer tokens, query strings, or request bodies.
        segment = urlsplit(self.path).path.split('/')[1]
        if segment not in ('api', 'u', 'static', 'healthz', ''):
            segment = 'other'
        print(f'{self.command} /{segment} {code}', flush=True)

    def log_message(self, format, *args):
        pass

    def reply(self, status, value, content_type='application/json; charset=utf-8'):
        if content_type.startswith('application/json'):
            body = json.dumps(value, ensure_ascii=False).encode()
        else:
            body = value if isinstance(value, bytes) else value.encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if urlsplit(self.path).path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        self.reply(code, {'error': message or 'Request failed'})

    def read_body(self):
        if self.headers.get('Transfer-Encoding'):
            self.close_connection = True
            raise HTTPError(400, 'Transfer-Encoding is not supported')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise HTTPError(400, 'Invalid Content-Length')
        if not 0 <= length <= 10240:
            self.close_connection = True
            raise HTTPError(413, 'Request body must be at most 10 KB')
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, 'Invalid JSON body')
        if not isinstance(body, dict):
            raise HTTPError(400, 'JSON body must be an object')
        return body

    def dispatch(self):
        conn = None
        try:
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                raise HTTPError(400, 'Invalid Content-Length')
            if not 0 <= length <= 10240:
                self.close_connection = True
                raise HTTPError(413, 'Request body must be at most 10 KB')
            path = urlsplit(self.path).path
            if self.command == 'GET':
                if path == '/':
                    return self.reply(200, 'clothesRec v2 -- ask Ryan for your personal link.', 'text/plain; charset=utf-8')
                if path == '/healthz':
                    return self.reply(200, 'ok', 'text/plain; charset=utf-8')
                if path in ('/static/app.js', '/static/app.css'):
                    name = path.rsplit('/', 1)[1]
                    kind = 'text/javascript' if name.endswith('.js') else 'text/css'
                    return self.reply(200, (STATIC / name).read_bytes(), kind + '; charset=utf-8')
            parts = path.strip('/').split('/')
            conn = db.connect()
            if self.command == 'GET' and len(parts) == 2 and parts[0] == 'u':
                if not conn.execute('SELECT id FROM people WHERE token=?', (parts[1],)).fetchone():
                    raise HTTPError(404, 'Not found')
                return self.reply(200, (STATIC / 'app.html').read_bytes(), 'text/html; charset=utf-8')
            if len(parts) < 4 or parts[:2] != ['api', 'u']:
                raise HTTPError(404, 'Not found')
            person = conn.execute('SELECT id FROM people WHERE token=?', (parts[2],)).fetchone()
            if not person:
                raise HTTPError(404, 'Not found')
            result = self.api(conn, person['id'], parts[3:])
            conn.commit()
            self.reply(200, result)
        except HTTPError as exc:
            self.reply(exc.status, {'error': str(exc)})
        except summarize.SpendGuardError as exc:
            self.reply(429, {'error': str(exc)})
        except summarize.TooFewRatingsError as exc:
            self.reply(400, {'error': str(exc)})
        except sqlite3.IntegrityError:
            self.reply(400, {'error': 'Invalid record'})
        except Exception:
            # No request URLs or provider credentials in logs or client errors.
            self.reply(500, {'error': 'Request failed'})
        finally:
            if conn is not None:
                conn.close()

    def api(self, conn, person_id, parts):
        method = self.command
        if method == 'GET' and parts == ['items']:
            query = parse_qs(urlsplit(self.path).query)
            try:
                offset = int(query.get('offset', ['0'])[0])
                limit = int(query.get('limit', ['48'])[0])
            except ValueError:
                raise HTTPError(400, 'offset and limit must be integers')
            if offset < 0 or not 1 <= limit <= 60:
                raise HTTPError(400, 'offset must be nonnegative and limit must be 1–60')
            mode = query.get('filter', ['all'])[0]
            conditions = {'all': '1', 'unrated': 'f.id IS NULL', 'rated': 'f.id IS NOT NULL',
                          'dislike': "f.reaction='dislike'", 'like': "f.reaction='like'", 'love': "f.reaction='love'"}
            if mode not in conditions:
                raise HTTPError(400, 'Unknown filter')
            join = 'FROM items i LEFT JOIN feedback f ON f.item_id=i.id AND f.person_id=? WHERE ' + conditions[mode]
            total = conn.execute('SELECT count(*) ' + join, (person_id,)).fetchone()[0]
            rows = conn.execute('''SELECT i.*, f.id AS feedback_id, f.reaction, f.note,
                                f.updated_at AS feedback_updated_at ''' + join +
                                ' ORDER BY i.source, i.title, i.id LIMIT ? OFFSET ?',
                                (person_id, limit, offset)).fetchall()
            items = []
            for row in rows:
                item = db.display_item(row)
                feedback_id = item.pop('feedback_id')
                feedback = {'id': feedback_id, 'reaction': item.pop('reaction'),
                            'note': item.pop('note'), 'updated_at': item.pop('feedback_updated_at')}
                item['feedback'] = feedback if feedback_id is not None else None
                items.append(item)
            return {'total': total, 'items': items}
        if len(parts) == 2 and parts[0] == 'feedback' and method in ('PUT', 'DELETE'):
            item_id = unquote(parts[1])
            if not conn.execute('SELECT id FROM items WHERE id=?', (item_id,)).fetchone():
                raise HTTPError(404, 'Item not found')
            if method == 'DELETE':
                db.clear_feedback(conn, person_id, item_id)
                return {'ok': True}
            body = self.read_body()
            reaction, note = body.get('reaction'), body.get('note', '')
            if reaction not in REACTIONS or not isinstance(note, str) or len(note) > 500:
                raise HTTPError(400, 'Use dislike, like, or love and a note of at most 500 characters')
            return db.set_feedback(conn, person_id, item_id, reaction, note)
        if method == 'GET' and parts == ['stats']:
            counts = {reaction: 0 for reaction in REACTIONS}
            for row in conn.execute('SELECT reaction, count(*) AS n FROM feedback WHERE person_id=? GROUP BY reaction', (person_id,)):
                counts[row['reaction']] = row['n']
            counts['catalog_size'] = conn.execute('SELECT count(*) FROM items').fetchone()[0]
            counts['last_checked_at'] = conn.execute('SELECT max(last_checked_at) FROM items').fetchone()[0]
            counts['rejection_count'] = conn.execute('SELECT count(*) FROM rejections').fetchone()[0]
            counts['fetch_runs'] = [dict(row) for row in conn.execute('''SELECT * FROM fetch_runs
                WHERE id IN (SELECT max(id) FROM fetch_runs GROUP BY source) ORDER BY source''')]
            return counts
        if method == 'GET' and parts == ['rejections']:
            return [dict(row) for row in conn.execute('SELECT * FROM rejections ORDER BY source, external_id')]
        if method == 'GET' and parts == ['summary', 'preview']:
            return {'examples': summarize.select_examples(conn, person_id),
                    'request': summarize.preview(conn, person_id)}
        if method == 'POST' and parts == ['summary']:
            if self.headers.get('Content-Length', '0') != '0':
                self.read_body()
            result = summarize.run(conn, person_id)
            if result.get('error'):
                raise HTTPError(502, result['error'])
            return result
        if method == 'GET' and parts == ['summaries']:
            return [dict(row) for row in conn.execute('SELECT * FROM summaries WHERE person_id=? ORDER BY id DESC', (person_id,))]
        if method == 'PUT' and len(parts) == 2 and parts[0] == 'summaries':
            body = self.read_body()
            text = body.get('edited_text')
            if not isinstance(text, str):
                raise HTTPError(400, 'edited_text must be text')
            cursor = conn.execute('UPDATE summaries SET edited_text=? WHERE id=? AND person_id=?', (text, parts[1], person_id))
            if not cursor.rowcount:
                raise HTTPError(404, 'Summary not found')
            return dict(conn.execute('SELECT * FROM summaries WHERE id=? AND person_id=?', (parts[1], person_id)).fetchone())
        raise HTTPError(404, 'Not found')

    do_GET = dispatch
    do_PUT = dispatch
    do_POST = dispatch
    do_DELETE = dispatch


def main():
    server = ThreadingHTTPServer((os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8090'))), Handler)
    print(f'clothesRec v2 listening on {server.server_address[0]}:{server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
