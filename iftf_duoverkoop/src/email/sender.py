"""One-off Mailgun API smoke test helper.

Environment variables required:
- MAILGUN_API_KEY
- MAILGUN_DOMAIN
- MAILGUN_TO
Optional:
- MAILGUN_API_BASE_URL (default: https://api.eu.mailgun.net)
- MAILGUN_FROM_EMAIL (default: postmaster@<MAILGUN_DOMAIN>)
"""
import os

import requests


def send_simple_message():
    api_key = os.environ.get('MAILGUN_API_KEY', '').strip()
    domain = os.environ.get('MAILGUN_DOMAIN', '').strip()
    recipient = os.environ.get('MAILGUN_TO', '').strip()
    base_url = os.environ.get('MAILGUN_API_BASE_URL', 'https://api.eu.mailgun.net').rstrip('/')
    from_email = os.environ.get('MAILGUN_FROM_EMAIL', f'postmaster@{domain}')

    if not api_key or not domain or not recipient:
        raise RuntimeError('Missing MAILGUN_API_KEY, MAILGUN_DOMAIN or MAILGUN_TO env var.')

    return requests.post(
        f'{base_url}/v3/{domain}/messages',
        auth=('api', api_key),
        data={
            'from': from_email,
            'to': recipient,
            'subject': 'Mailgun smoke test',
            'text': 'This is a Mailgun API connectivity test.',
        },
        timeout=15,
    )


if __name__ == '__main__':
    response = send_simple_message()
    print(f'Status: {response.status_code}')
    print(response.text)
