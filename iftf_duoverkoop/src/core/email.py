"""Async confirmation email sending with status tracking and Mailgun API support."""
import logging
import mimetypes
import threading
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext as _

from iftf_duoverkoop.src.core.models import EmailCampaign, EmailCampaignRecipient, EmailTemplateSettings, Purchase

logger = logging.getLogger(__name__)


def _display_timezone() -> ZoneInfo:
    tz_name = getattr(settings, 'TIME_ZONE', 'UTC') or 'UTC'
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo('UTC')


def _format_local_datetime(value, fmt: str = '%d/%m/%Y %H:%M') -> str:
    return dj_timezone.localtime(value, _display_timezone()).strftime(fmt)


def _required_mail_info_text() -> str:
    return (
        'Important information:\n'
        '1. This email only confirms your duo ticket sale. Practical details are shared by each association.\n'
        '2. Information sent by the associations is the source of truth. Associations may send separate tickets through their own systems.\n'
        '3. Keep your verification code easily accessible. It may be used at performance entrances, depending on association policy.\n'
        '4. Report disputes or incorrect recipient information to https://iftf.be/contact/.\n'
        '5. More information: https://iftf.be\n'
    )


def _required_mail_info_html() -> str:
    return (
        '<div style="margin-top:16px;padding-top:12px;border-top:1px solid {{ border_color }};">'
        '<p style="margin:0 0 8px 0;"><strong>Important information</strong></p>'
        '<ol style="margin:0 0 10px 20px;padding:0;">'
        '<li style="margin-bottom:6px;">This email only confirms your duo ticket sale. Practical details are shared by each association.</li>'
        '<li style="margin-bottom:6px;">Information sent by the associations is the source of truth. Associations may send separate tickets through their own systems.</li>'
        '<li style="margin-bottom:6px;">Keep your verification code easily accessible. It may be used at performance entrances, depending on association policy.</li>'
        '<li style="margin-bottom:6px;">Report disputes or incorrect recipient information to <a href="https://iftf.be/contact/">https://iftf.be/contact/</a>.</li>'
        '<li>More information: <a href="https://iftf.be">https://iftf.be</a></li>'
        '</ol>'
        '</div>'
    )


def _ensure_subject_has_code(subject: str, verification_code: str) -> str:
    subject_clean = (subject or '').strip()
    code_clean = (verification_code or '').strip()
    if not code_clean:
        return subject_clean
    if code_clean.lower() in subject_clean.lower():
        return subject_clean
    if subject_clean:
        return f'{subject_clean} [{code_clean}]'
    return code_clean


def _inject_logo_into_html(html: str, logo_url: str) -> str:
    if not logo_url:
        return html
    if logo_url in html:
        return html

    logo_block = (
        '<div style="text-align:center;margin:0 0 14px 0;">'
        f'<img src="{logo_url}" alt="IFTF" style="max-height:64px;max-width:220px;">'
        '</div>'
    )
    lower_html = html.lower()
    body_start = lower_html.find('<body')
    if body_start >= 0:
        body_tag_end = lower_html.find('>', body_start)
        if body_tag_end >= 0:
            insert_at = body_tag_end + 1
            return html[:insert_at] + logo_block + html[insert_at:]
    return logo_block + html


def _append_required_info(text_body: str, html_body: str, border_color: str) -> tuple[str, str]:
    required_text = _required_mail_info_text()
    required_html = _required_mail_info_html().replace('{{ border_color }}', border_color or '#dbe3ec')

    text_out = text_body
    if 'https://iftf.be/contact/' not in (text_body or ''):
        text_out = (text_body or '').rstrip() + '\n\n' + required_text

    html_out = html_body
    if 'https://iftf.be/contact/' not in (html_body or ''):
        html_out = (html_body or '') + required_html
    return text_out, html_out


def _load_iftf_logo_inline_attachment() -> tuple[str, bytes, str] | None:
    """Return inline logo tuple (filename, bytes, content_type) when available."""
    candidate_paths = [
        Path(settings.BASE_DIR) / 'iftf_duoverkoop' / 'static' / 'Site logo.png',
        Path(getattr(settings, 'STATIC_ROOT', Path(settings.BASE_DIR) / 'staticfiles')) / 'Site logo.png',
    ]
    for path in candidate_paths:
        try:
            if path.exists() and path.is_file():
                content_type = mimetypes.guess_type(str(path))[0] or 'image/png'
                return 'iftf-logo.png', path.read_bytes(), content_type
        except Exception:
            continue
    return None


def _inline_logo_for_mail_html(html_body: str) -> tuple[str, list[tuple[str, bytes, str]]]:
    """
    Replace configured logo URL with CID reference and return inline attachment.

    Many email clients do not load relative/static URLs in mail HTML.
    """
    html_out = html_body or ''
    logo_url = (getattr(settings, 'IFTF_LOGO_URL', '') or '').strip()
    logo_attachment = _load_iftf_logo_inline_attachment()
    if logo_attachment is None:
        return html_out, []

    cid_ref = 'cid:iftf-logo.png'

    if logo_url and logo_url in html_out:
        html_out = html_out.replace(logo_url, cid_ref)
        return html_out, [logo_attachment]

    if cid_ref in html_out:
        return html_out, [logo_attachment]

    return html_out, []


def render_email_html_preview(
    html_template: str,
    style_context: dict | None = None,
    purchase: Purchase | None = None,
) -> tuple[str, str | None]:
    """
    Render an email HTML template using sample data for dashboard preview.

    Returns (rendered_html, error_message). If rendering fails, the fallback
    HTML is rendered and error_message contains the parse/runtime issue.
    """
    sample_context = {
        'name': 'Alex Example',
        'email': 'alex@example.com',
        'verification_code': 'happy-tree-button',
        'performance1': 'Fri 22 Mar - AMUZEMENT - Comedy Night',
        'performance2': 'Sat 23 Mar - HISTORIA - Mystery Play',
        'purchase_date': '22/03/2026 19:30',
        'total_price': '18.00',
        'culture_card_line': 'Culture card applied (student ID: r0123456).',
        'primary_color': '#0d6efd',
        'accent_color': '#198754',
        'background_color': '#f5f7fb',
        'card_background_color': '#ffffff',
        'border_color': '#dbe3ec',
        'content_width': 640,
        'footer_text': 'See you at the IFTF performances.',
        'iftf_logo_url': getattr(settings, 'IFTF_LOGO_URL', ''),
        'iftf_home_url': 'https://iftf.be',
        'iftf_contact_url': 'https://iftf.be/contact/',
    }
    if purchase is not None:
        sample_context.update(_build_render_context(purchase))
    if style_context:
        sample_context.update(style_context)

    fallback_html = (
        '<html><body style="font-family:Arial,sans-serif;">'
        '<h2>IFTF DuoVerkoop Preview</h2>'
        '<p>Hi <strong>{{ name }}</strong>, your duo ticket is confirmed.</p>'
        '<p><strong>Ticket 1:</strong> {{ performance1 }}<br>'
        '<strong>Ticket 2:</strong> {{ performance2 }}<br>'
        '<strong>Total paid:</strong> EUR {{ total_price }}</p>'
        '<p><strong>Verification code:</strong> {{ verification_code }}</p>'
        '<p><a href="https://iftf.be">https://iftf.be</a></p>'
        '</body></html>'
    )

    try:
        rendered = Template(html_template or fallback_html).render(Context(sample_context))
        return rendered, None
    except TemplateSyntaxError as exc:
        rendered = Template(fallback_html).render(Context(sample_context))
        return rendered, f'Template syntax error: {exc}'
    except Exception as exc:
        rendered = Template(fallback_html).render(Context(sample_context))
        return rendered, f'Preview render error: {exc}'


def _ics_escape(value: str) -> str:
    return (
        (value or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\r\n', '\\n')
        .replace('\n', '\\n')
    )


def build_purchase_ics_bytes(purchase: Purchase) -> bytes:
    """Generate an ICS file containing both performances for this purchase."""
    tz = _display_timezone()
    dtstamp = dj_timezone.now().astimezone(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')
    tzid = getattr(tz, 'key', str(tz))

    events = []
    for index, performance in enumerate((purchase.ticket1, purchase.ticket2), start=1):
        start = dj_timezone.localtime(performance.date, tz)
        end = start + timedelta(hours=2)
        association_name = performance.association.name
        if performance.association.address:
            location_value = performance.association.address.single_line()
            maps_url = (
                'https://www.google.com/maps/search/?api=1&query='
                f'{quote_plus(performance.association.address.google_maps_query())}'
            )
        else:
            location_value = association_name
            maps_url = ''

        description = (
            f'{_ics_escape("Ticket purchased by " + purchase.name)} as IFTF DuoTicket. '
            f"Don't forget to bring your secret code: {_ics_escape(purchase.verification_code)}"
        )
        if maps_url:
            description = f'{description}. {_ics_escape("Maps: " + maps_url)}'

        events.append(
            [
                'BEGIN:VEVENT',
                f'UID:{purchase.pk}-{performance.key}-{index}@iftfduoverkoop',
                f'DTSTAMP:{dtstamp}',
                f'DTSTART;TZID={tzid}:{start.strftime("%Y%m%dT%H%M%S")}',
                f'DTEND;TZID={tzid}:{end.strftime("%Y%m%dT%H%M%S")}',
                f'SUMMARY:{_ics_escape(f"{association_name} - {performance.name}")}',
                f'LOCATION:{_ics_escape(location_value)}',
                f'DESCRIPTION:{description}',
                'END:VEVENT',
            ]
        )
        if maps_url:
            events[-1].insert(-1, f'URL:{_ics_escape(maps_url)}')

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//IFTF//DuoVerkoop//NL',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'NAME:IFTF Duoverkoop tickets',
        'X-WR-CALNAME:IFTF Duoverkoop tickets',
        'X-WR-CALDESC:IFTF duo ticket purchase containing two performances',
    ]
    for event in events:
        lines.extend(event)
    lines.append('END:VCALENDAR')
    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')


def _load_template_settings() -> EmailTemplateSettings | None:
    try:
        return EmailTemplateSettings.get_solo()
    except Exception as exc:
        logger.warning('Email template settings unavailable, using fallback templates: %s', exc)
        return None


def _safe_render(template_string: str, context: dict, fallback: str) -> str:
    try:
        return Template(template_string).render(Context(context))
    except TemplateSyntaxError as exc:
        logger.error('Invalid email template syntax, falling back to defaults: %s', exc)
        return Template(fallback).render(Context(context))
    except Exception as exc:
        logger.error('Unexpected email template render failure, falling back to defaults: %s', exc)
        return Template(fallback).render(Context(context))


def _build_render_context(purchase: Purchase) -> dict:
    culture_card_line = ''
    if purchase.has_culture_card and purchase.student_id:
        culture_card_line = f'Culture card applied (student ID: {purchase.student_id}).'

    return {
        'name': purchase.name,
        'email': purchase.email,
        'verification_code': purchase.verification_code,
        'performance1': purchase.ticket1.selection(),
        'performance2': purchase.ticket2.selection(),
        'purchase_date': _format_local_datetime(purchase.date),
        'total_price': f'{purchase.total_price():.2f}',
        'culture_card_line': culture_card_line,
        'iftf_home_url': 'https://iftf.be',
        'iftf_contact_url': 'https://iftf.be/contact/',
        'iftf_logo_url': getattr(settings, 'IFTF_LOGO_URL', ''),
    }


def _build_confirmation_parts(purchase: Purchase, subject: str | None, message: str | None) -> tuple[str, str, str]:
    context = _build_render_context(purchase)
    tpl = _load_template_settings()

    fallback_subject = 'IFTF duo ticket confirmation - {{ verification_code }}'
    fallback_text = (
        'Hi {{ name }},\n\n'
        'Your duo ticket was registered successfully.\n\n'
        'Ticket 1: {{ performance1 }}\n'
        'Ticket 2: {{ performance2 }}\n'
        'Order date: {{ purchase_date }}\n'
        'Total paid: EUR {{ total_price }}\n\n'
        'Verification code: {{ verification_code }}\n\n'
        'This email only confirms your duo ticket sale. Practical details are shared by each association.\n'
        'Association communication is the source of truth. Keep watching your email for further info.\n'
        'Report disputes to https://iftf.be/contact/. More info: https://iftf.be\n'
    )
    fallback_html = (
        '<html><body>'
        '<div style="padding:12px 14px;background:{{ primary_color }};color:#fff;display:flex;align-items:center;gap:16px;">'
        '{% if iftf_logo_url %}'
        '<img src="{{ iftf_logo_url }}" alt="IFTF" '
        'style="max-height:28px;max-width:28px;object-fit:contain;background:#fff;border-radius:4px;padding:2px;">'
        '{% endif %}'
        '<h2 style="margin:0;font-size:20px;">IFTF DuoVerkoop</h2>'
        '</div>'
        '<p>Hi <strong>{{ name }}</strong>, your duo ticket is confirmed.</p>'
        '<p><strong>Ticket 1:</strong> {{ performance1 }}<br>'
        '<strong>Ticket 2:</strong> {{ performance2 }}<br>'
        '<strong>Order date:</strong> {{ purchase_date }}<br>'
        '<strong>Total paid:</strong> EUR {{ total_price }}</p>'
        '<p><strong>Verification code:</strong> {{ verification_code }}</p>'
        '<p>This email only confirms your duo ticket sale. Practical details are shared by each association.</p>'
        '<p>Association communication is the source of truth. Keep watching your email for further info.</p>'
        '<p>Report disputes to <a href="https://iftf.be/contact/">https://iftf.be/contact/</a>. '
        'More info: <a href="https://iftf.be">https://iftf.be</a>.</p>'
        '</body></html>'
    )

    if tpl is not None:
        context.update({
            'primary_color': tpl.primary_color,
            'accent_color': tpl.accent_color,
            'background_color': tpl.background_color,
            'card_background_color': tpl.card_background_color,
            'border_color': tpl.border_color,
            'content_width': tpl.content_width,
            'footer_text': tpl.footer_text,
        })
        subject_out = _safe_render(tpl.subject_template, context, fallback_subject)
        text_out = _safe_render(tpl.text_template, context, fallback_text)
        html_out = _safe_render(tpl.html_template, context, fallback_html)
    else:
        subject_out = _safe_render(fallback_subject, context, fallback_subject)
        text_out = _safe_render(message or fallback_text, context, fallback_text)
        html_out = _safe_render(fallback_html, context, fallback_html)

    if subject:
        subject_out = subject
    if message and tpl is None:
        text_out = message

    border_color = context.get('border_color', '#dbe3ec')
    text_out, html_out = _append_required_info(text_out, html_out, border_color)
    html_out = _inject_logo_into_html(html_out, context.get('iftf_logo_url', ''))
    subject_out = _ensure_subject_has_code(subject_out, purchase.verification_code)
    return subject_out.strip(), text_out.strip(), html_out


def _send_via_mailgun_raw(
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> None:
    api_key = (getattr(settings, 'MAILGUN_API_KEY', '') or '').strip()
    domain = (getattr(settings, 'MAILGUN_DOMAIN', '') or '').strip()
    base_url = (getattr(settings, 'MAILGUN_API_BASE_URL', 'https://api.eu.mailgun.net') or '').rstrip('/')
    from_email = (getattr(settings, 'MAILGUN_FROM_EMAIL', '') or '').strip()
    from_name = (getattr(settings, 'MAILGUN_FROM_NAME', '') or '').strip()
    timeout = int(getattr(settings, 'MAIL_REQUEST_TIMEOUT', 15))

    if not api_key or not domain or not from_email:
        raise ValueError('Mailgun settings are incomplete. Required: MAILGUN_API_KEY, MAILGUN_DOMAIN, MAILGUN_FROM_EMAIL.')

    from_header = f'{from_name} <{from_email}>' if from_name else from_email
    endpoint = f'{base_url}/v3/{domain}/messages'

    files_payload = []
    for filename, payload, content_type in attachments or []:
        files_payload.append(('attachment', (filename, payload, content_type)))

    html_payload, inline_attachments = _inline_logo_for_mail_html(html_body)

    for filename, payload, content_type in inline_attachments:
        files_payload.append(('inline', (filename, payload, content_type)))

    response = requests.post(
        endpoint,
        auth=('api', api_key),
        data={
            'from': from_header,
            'to': recipient,
            'subject': subject,
            'text': text_body,
            'html': html_payload,
        },
        files=files_payload,
        timeout=timeout,
    )
    response.raise_for_status()


def _send_via_mailgun(recipient: str, subject: str, text_body: str, html_body: str, purchase: Purchase) -> None:
    # A neutral filename gives clearer attachment UX in clients like Gmail.
    ics_filename = 'IFTF-Duoverkoop-tickets.ics'
    ics_bytes = build_purchase_ics_bytes(purchase)
    _send_via_mailgun_raw(
        recipient=recipient,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        attachments=[(ics_filename, ics_bytes, 'text/calendar')],
    )


def _send_and_update(purchase_id: int, subject: str | None, message: str | None) -> None:
    """
    Worker run in a daemon thread.  Sends the mail and persists the result.
    Never raises – all exceptions are caught and logged.
    """
    try:
        purchase = Purchase.objects.select_related(
            'ticket1__association__address',
            'ticket2__association__address',
        ).get(pk=purchase_id)
        resolved_subject, text_body, html_body = _build_confirmation_parts(purchase, subject, message)
        _send_via_mailgun(
            recipient=purchase.email,
            subject=resolved_subject,
            text_body=text_body,
            html_body=html_body,
            purchase=purchase,
        )
        Purchase.objects.filter(pk=purchase_id).update(email_status=Purchase.EMAIL_SENT)
        logger.info('Confirmation email sent for purchase %s to %s', purchase_id, purchase.email)
    except Exception as exc:
        Purchase.objects.filter(pk=purchase_id).update(email_status=Purchase.EMAIL_FAILED)
        logger.error(
            'Failed to send confirmation email for purchase %s: %s',
            purchase_id, exc,
        )


def send_confirmation_email_async(purchase: Purchase, subject: str | None = None, message: str | None = None) -> None:
    """
    Dispatch a confirmation email in a background thread.

    The purchase status is set to PENDING immediately; the thread will
    update it to SENT or FAILED once the SMTP call resolves.
    Does nothing (and sets NOT_SENT) when SEND_EMAILS is False.
    """
    if not settings.SEND_EMAILS:
        Purchase.objects.filter(pk=purchase.pk).update(email_status=Purchase.EMAIL_NOT_SENT)
        purchase.email_status = Purchase.EMAIL_NOT_SENT
        return

    # Mark as PENDING right away so the field is never left at its default
    # in case the thread is slow.
    Purchase.objects.filter(pk=purchase.pk).update(email_status=Purchase.EMAIL_PENDING)
    purchase.email_status = Purchase.EMAIL_PENDING

    t = threading.Thread(
        target=_send_and_update,
        args=(purchase.pk, subject, message),
        daemon=True,
        name=f"email-purchase-{purchase.pk}",
    )
    t.start()


def build_confirmation_message(purchase: Purchase) -> tuple[str, str]:
    """Backward-compatible wrapper used by existing views."""
    subject = _('email.subject')
    message = _('email.message_with_code') % {
        'name': purchase.name,
        'performance1': purchase.ticket1.selection(),
        'performance2': purchase.ticket2.selection(),
        'date': _format_local_datetime(purchase.date),
        'verification_code': purchase.verification_code,
    }
    subject = _ensure_subject_has_code(subject, purchase.verification_code)
    return subject, message


def _campaign_purchase_queryset(campaign: EmailCampaign):
    qs = Purchase.objects.select_related(
        'ticket1', 'ticket1__association',
        'ticket2', 'ticket2__association',
    ).order_by('-date')

    if campaign.audience_type == EmailCampaign.AUDIENCE_ASSOCIATIONS:
        assoc_ids = list(campaign.audience_associations.values_list('pk', flat=True))
        qs = qs.filter(ticket1__association__in=assoc_ids) | qs.filter(ticket2__association__in=assoc_ids)
        qs = qs.distinct()
    elif campaign.audience_type == EmailCampaign.AUDIENCE_PERFORMANCE and campaign.audience_performance_id:
        perf = campaign.audience_performance
        qs = qs.filter(ticket1=perf) | qs.filter(ticket2=perf)
        qs = qs.distinct()

    return qs


def _build_campaign_recipient_rows(campaign: EmailCampaign) -> list[EmailCampaignRecipient]:
    purchases = _campaign_purchase_queryset(campaign)

    # Deduplicate by email to avoid sending duplicates for customers
    # with multiple purchases.
    by_email: dict[str, Purchase] = {}
    for purchase in purchases:
        email = (purchase.email or '').strip().lower()
        if not email or email in by_email:
            continue
        by_email[email] = purchase

    rows: list[EmailCampaignRecipient] = []
    for email, purchase in by_email.items():
        rows.append(
            EmailCampaignRecipient(
                campaign=campaign,
                purchase=purchase,
                email=email,
                customer_name=purchase.name,
                status=EmailCampaignRecipient.STATUS_PENDING,
                audience_context=(
                    f'{purchase.ticket1.association.name}/{purchase.ticket1.key}; '
                    f'{purchase.ticket2.association.name}/{purchase.ticket2.key}'
                ),
            )
        )
    return rows


def _render_campaign_parts(campaign: EmailCampaign, purchase: Purchase) -> tuple[str, str, str]:
    context = _build_render_context(purchase)
    tpl = _load_template_settings()
    if tpl is not None:
        context.update({
            'primary_color': tpl.primary_color,
            'accent_color': tpl.accent_color,
            'background_color': tpl.background_color,
            'card_background_color': tpl.card_background_color,
            'border_color': tpl.border_color,
            'content_width': tpl.content_width,
            'footer_text': tpl.footer_text,
        })

    fallback_subject = 'IFTF follow-up - {{ verification_code }}'
    fallback_text = campaign.text_template or 'Hi {{ name }},\n\n{{ culture_card_line }}'
    fallback_html = campaign.html_template or '<html><body><p>Hi {{ name }}</p></body></html>'

    subject = _safe_render(campaign.subject_template or fallback_subject, context, fallback_subject).strip()
    text = _safe_render(campaign.text_template or fallback_text, context, fallback_text).strip()
    html = _safe_render(campaign.html_template or fallback_html, context, fallback_html)
    text, html = _append_required_info(text, html, context.get('border_color', '#dbe3ec'))
    html = _inject_logo_into_html(html, context.get('iftf_logo_url', ''))
    subject = _ensure_subject_has_code(subject, purchase.verification_code)
    return subject, text, html


def _send_campaign_and_update(campaign_id: int) -> None:
    try:
        campaign = EmailCampaign.objects.select_related('audience_performance').prefetch_related('audience_associations').get(pk=campaign_id)
        campaign.status = EmailCampaign.STATUS_RUNNING
        campaign.started_at = dj_timezone.now()
        campaign.error_message = ''
        campaign.save(update_fields=['status', 'started_at', 'error_message'])

        recipients = _build_campaign_recipient_rows(campaign)
        EmailCampaignRecipient.objects.filter(campaign=campaign).delete()
        if recipients:
            EmailCampaignRecipient.objects.bulk_create(recipients)

        total = len(recipients)
        sent = 0
        failed = 0

        for row in EmailCampaignRecipient.objects.select_related('purchase').filter(campaign=campaign):
            try:
                if row.purchase is None:
                    raise ValueError('No linked purchase found for recipient.')
                subject, text_body, html_body = _render_campaign_parts(campaign, row.purchase)
                _send_via_mailgun_raw(
                    recipient=row.email,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                    attachments=None,
                )
                row.status = EmailCampaignRecipient.STATUS_SENT
                row.sent_at = dj_timezone.now()
                row.error_message = ''
                row.save(update_fields=['status', 'sent_at', 'error_message'])
                sent += 1
            except Exception as exc:
                row.status = EmailCampaignRecipient.STATUS_FAILED
                row.error_message = str(exc)[:2000]
                row.save(update_fields=['status', 'error_message'])
                failed += 1

        campaign.total_recipients = total
        campaign.sent_count = sent
        campaign.failed_count = failed
        campaign.finished_at = dj_timezone.now()
        if failed and sent:
            campaign.status = EmailCampaign.STATUS_PARTIAL_FAILED
        elif failed and not sent:
            campaign.status = EmailCampaign.STATUS_FAILED
        else:
            campaign.status = EmailCampaign.STATUS_SUCCEEDED
        campaign.save(update_fields=['total_recipients', 'sent_count', 'failed_count', 'finished_at', 'status'])
    except Exception as exc:
        EmailCampaign.objects.filter(pk=campaign_id).update(
            status=EmailCampaign.STATUS_FAILED,
            finished_at=dj_timezone.now(),
            error_message=str(exc)[:2000],
        )
        logger.error('Email campaign %s failed: %s', campaign_id, exc)


def send_email_campaign_async(campaign: EmailCampaign) -> None:
    """Queue a follow-up campaign send in a background thread."""
    t = threading.Thread(
        target=_send_campaign_and_update,
        args=(campaign.pk,),
        daemon=True,
        name=f'email-campaign-{campaign.pk}',
    )
    t.start()


