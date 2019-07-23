#!/usr/bin/env python3
import email.message
import json
import html
import logging
import mailjet_rest
import pystache
import os
import requests
import re
import time
import signal
import smtplib
import sys
from urllib.parse import urljoin


products_cache = dict()

html_template = """
<html>
<body>
    <p>Search URL <a target="_blank" href="{{url}}">{{url}}</a></p>
    {{#products}}
    <p>
        <a target="_blank" href="{{productUrl}}"><img src="{{thumbnailImageUrl}}">
        {{brandName}} {{productName}}</a> <font color="red">{{price}}</font>
    </p>
    {{/products}}
</body>
</html>
"""


def sigterm_handler(_signo, _stack_frame):
    sys.exit(0)


def get_updates(url):
    product_updated = list()
    r = requests.get(url)
    if r.status_code == 200:
        emjson = re.search(r'<script>window\.__INITIAL_STATE__\s?=\s?(.*);<\/script>', r.text)
        if emjson:
            try:
                if url.startswith('https://www.6pm.com/p/'):
                    detail = json.loads(emjson.group(1))['product']['detail']
                    detail['productUrl'] = url
                    detail['thumbnailImageUrl'] = detail['defaultImageUrl']
                    detail['price'] = json.loads(emjson.group(1))['pixelServer']['data']['trackingPayload']['product']['price']
                    products = [detail]
                else:
                    products = json.loads(emjson.group(1))['products']['list']
                products_prev = products_cache.get(url)
                if products_prev:
                    for product in products:
                        product['productName'] = html.unescape(product['productName'])
                        product['productUrl'] = urljoin('https://www.6pm.com/', product['productUrl'])
                        product['thumbnailImageUrl'] = urljoin('https://www.6pm.com/', product['thumbnailImageUrl'])
                        product_prev = next((item for item in products_prev if item['productUrl'] in product['productUrl']), None)
                        if product_prev:
                            current_price = float(product['price'].replace('$', ''))
                            prev_price = float(product_prev['price'].replace('$', ''))
                            if current_price < prev_price:
                                logging.info('{} : ${} < ${}'.format(product['productUrl'], current_price, prev_price))
                                product_updated.append(product)
                        else:
                            logging.info('{} : new product with {}'.format(product['productUrl'], product['price']))
                            product_updated.append(product)
                products_cache[url] = products
            except KeyError as e:
                logging.error('I got a KeyError with reason {}'.format(e))
        else:
            logging.error('Problem with extract JSON from HTML ' + url)
    else:
        logging.error('Error {} get url {}'.format(r.status_code, url))
    return product_updated


def send_email_smtp(to, body):
    msg = email.message.Message()
    msg['Subject'] = '6pm.com updates'
    msg['From'] = '6pm-checker@example.com'
    msg['To'] = to
    msg.add_header('Content-Type', 'text/html')
    msg.set_payload(body)
    try:
        s = smtplib.SMTP('localhost')
        s.sendmail(msg['From'], [msg['To']], msg.as_string())
    except Exception as e:
        logging.error('Failed send email: {}'.format(e))
    s.quit()


def send_email_mailjet(to, body):
    mailjet = mailjet_rest.Client(auth=(MJ_API_KEY, MJ_API_SECRET), version='v3.1')
    data = {
        'Messages': [{
            "From": {
                "Email": "6pm-checker@example.com",
                "Name": "6pm.com checker"
            },
            "To": [{
                "Email": to
            }],
            "Subject": "6pm.com updates",
            "HTMLPart": body
        }]
    }
    result = mailjet.send.create(data=data)
    if result.status_code == 200:
        logging.info('Send email to ' + to)
    else:
        logging.error('Send email failed to {}: {}'.format(to, result.json()))


if __name__ == "__main__":

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    logging.basicConfig(
        stream=sys.stdout,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        level=logging.INFO)

    MJ_API_KEY = os.getenv('MJ_APIKEY_PUBLIC')
    MJ_API_SECRET = os.getenv('MJ_APIKEY_PRIVATE')

    config = json.loads(os.getenv('CONFIG_6PM'))

    while True:
        for item in config:
            updates = get_updates(item['url'])
            if len(updates) > 0:
                html_result = pystache.render(html_template, {
                    'products': updates,
                    'url': item['url']
                })
                if MJ_API_KEY:
                    send_email_mailjet(item['mail'], html_result)
                else:
                    send_email_smtp(item['mail'], html_result)
            else:
                logging.debug('No updates for search ' + item['url'])
        time.sleep(600)
