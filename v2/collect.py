"""Collect approved Shopify feeds: python3 v2/collect.py [--max-pages N]."""
import argparse
from decimal import Decimal, InvalidOperation
import json
import time
from urllib.error import HTTPError
import urllib.request

import db

SOURCES = [
    {'domain': 'haruyama365.com', 'vendor': 'Kapital', 'condition': 'new'},
    {'domain': 'velourgarments.eu', 'condition': 'new'},
    {'domain': 'storymfg.com', 'condition': 'new'},
    {'domain': '3sixteen.com', 'condition': 'new'},
]
USER_AGENT = 'clothesRec/2 (personal project)'


def fetch_json(url):
    """Fetch JSON, retrying HTTP 429 at most three times (60s default, 120s cap)."""
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                raise
            delay = min(int(exc.headers.get('Retry-After', 60)), 120)
            print(f'rate limited, waiting {delay}s')
            time.sleep(delay)


def parse_product(product, source, currency, timestamp):
    """Raise ValueError for invalid records; leave unknown facts unknown."""
    external_id = product.get('id')
    if external_id is None or str(external_id).strip() == '':
        raise ValueError('Missing product id')
    if not product.get('handle') or not product.get('title'):
        raise ValueError('Missing product handle or title')
    images = [image['src'] for image in product.get('images', [])
              if isinstance(image, dict) and image.get('src')]
    if not images:
        raise ValueError('No product images')
    variants = product.get('variants') or []
    prices = []
    for variant in variants:
        value = variant.get('price')
        try:
            number = Decimal(str(value))
            if number.is_finite() and number >= 0:
                prices.append((number, str(value)))
        except InvalidOperation:
            pass
    size_options = [index + 1 for index, option in enumerate(product.get('options') or [])
                    if 'size' in str(option.get('name', '')).casefold()]
    sizes = []
    for variant in variants:
        values = ([variant.get(f'option{index}') for index in size_options]
                  if size_options else [variant.get('title')])
        for value in values:
            if value and value != 'Default Title' and value not in sizes:
                sizes.append(value)
    availability = [variant.get('available') for variant in variants]
    if any(value is True for value in availability):
        available = 1
    elif availability and all(value is False for value in availability):
        available = 0
    else:
        available = None
    tags = product.get('tags') or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
    domain = source['domain']
    return dict(id=f'{domain}:{external_id}', kind='listing', source=domain,
                brand=product.get('vendor') or '', title=product['title'],
                url=f"https://{domain}/products/{product['handle']}",
                image_url=images[0], image_urls=json.dumps(images),
                category=product.get('product_type') or None, tags=json.dumps(tags),
                price=min(prices)[1] if prices else None, currency=currency,
                condition=source['condition'], sizes=json.dumps(sizes), available=available,
                first_seen_at=timestamp, last_seen_at=timestamp, last_checked_at=timestamp)


def collect_source(conn, source, max_pages=None):
    domain = source['domain']
    started = db.now()
    pages = seen = 0
    error = None
    requested = False

    def request(path):
        nonlocal requested
        if requested:
            time.sleep(1.5)
        requested = True
        return fetch_json(f'https://{domain}/{path}')

    try:
        currency = None
        try:
            meta = request('meta.json')
            currency = meta.get('currency') or None
        except Exception:
            # Metadata is optional; products can retain an unknown currency.
            pass
        page = 1
        while max_pages is None or page <= max_pages:
            payload = request(f'products.json?limit=250&page={page}')
            products = payload['products']
            if not isinstance(products, list):
                raise ValueError('Products response is not a list')
            pages += 1
            if not products:
                break
            for product in products:
                if source.get('vendor') and str(product.get('vendor', '')).casefold() != source['vendor'].casefold():
                    continue
                seen += 1
                timestamp = db.now()
                try:
                    item = parse_product(product, source, currency, timestamp)
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    # A missing id still needs a stable, inspectable rejection key.
                    external_id = product.get('id')
                    if external_id is None or str(external_id).strip() == '':
                        external_id = 'missing-id:' + str(product.get('handle') or product.get('title') or 'unknown')
                    conn.execute('''INSERT INTO rejections VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(source, external_id) DO UPDATE SET
                        title=excluded.title, reason=excluded.reason, seen_at=excluded.seen_at''',
                        (domain, str(external_id), product.get('title'), str(exc), timestamp))
                else:
                    db.upsert_item(conn, item)
            conn.commit()
            page += 1
    except Exception as exc:
        # Keep any successfully collected records; failure never changes availability.
        conn.commit()
        error = str(exc)
    conn.execute('''INSERT INTO fetch_runs
        (source, started_at, finished_at, ok, pages, items_seen, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (domain, started, db.now(), int(error is None), pages, seen, error))
    conn.commit()
    print(f"{domain}: {'FAILED' if error else 'ok'}, {pages} pages, {seen} items"
          + (f' ({error})' if error else ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-pages', type=int)
    args = parser.parse_args()
    if args.max_pages is not None and args.max_pages < 1:
        parser.error('--max-pages must be positive')
    conn = db.connect()
    try:
        for source in SOURCES:
            collect_source(conn, source, args.max_pages)
            time.sleep(1.5)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
