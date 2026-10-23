"""Schema checks apply to closed and review-only residency records as well."""
import datetime as dt
import re
from urllib.parse import urlsplit

def validate_policy(record):
    p=record.get('residency_policy')
    if p is None:return
    if record.get('type')!='residency' or p.get('region') not in ('europe','outside_europe','unknown'):raise ValueError('Invalid residency geographic policy')
    def evidence(item):
        url=urlsplit(item.get('url',''))
        if url.scheme!='https' or not url.hostname or url.username or url.password:raise ValueError('Residency proof requires official HTTPS URL')
        stamp=dt.datetime.fromisoformat(item.get('verified_at','').replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError('Residency proof requires timezone-aware verification time')
    for key,item in p.get('components',{}).items():
        if key not in ('stipend','artist_fee','accommodation','studio','production','airfare','visa','other_transport'):raise ValueError('Unknown residency support component')
        if item.get('status') not in ('confirmed','needs_review','not_provided','not_required'):raise ValueError('Invalid residency support state')
        if item.get('status') in ('confirmed','not_provided','not_required'):evidence(item)
    for item in p.get('eligibility',{}).values():
        if item.get('status') not in ('eligible','ineligible','needs_review'):raise ValueError('Invalid residency eligibility state')
        if item.get('status') in ('eligible','ineligible'):evidence(item)
    a=p.get('airfare',{})
    if a.get('coverage') not in ('unknown','none','partial','round_trip_full','capped_round_trip'):raise ValueError('Invalid airfare coverage')
    if a.get('cap') is not None:
        if not isinstance(a['cap'],(float,int)) or isinstance(a['cap'],bool) or a['cap']<=0 or not re.fullmatch('[A-Z]{3}',a.get('currency','')):raise ValueError('Airfare cap requires positive amount and currency')
    if a.get('berlin_eligible') is True:
        departure=p.get('eligibility',{}).get('departure',{})
        if departure.get('status')!='eligible' or a.get('origin_rule') in (None,'unknown',''):raise ValueError('Berlin departure cannot be inferred from International')
        evidence(departure)
