"""Validate public records before deployment; standard library only."""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
def validate(payload, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(payload, dict) or not isinstance(payload.get('opportunities'), list):
        raise ValueError('opportunities must be an array')
    seen = set()
    for x in payload['opportunities']:
        if not isinstance(x, dict) or not x.get('name') or x.get('type') not in ('grant','residency'):
            raise ValueError('Invalid opportunity')
        if not x.get('id') or x['id'] in seen:
            raise ValueError('Missing or duplicate ID')
        seen.add(x['id'])
        u=urlsplit(x.get('url',''))
        if u.scheme!='https' or not u.hostname or u.username or u.password:
            raise ValueError('Official HTTPS URL required')
        if x.get('source_id')=='ncaf' and u.hostname!='www.ncafroc.org.tw':
            raise ValueError('NCAF requires official domain')
        if x.get('status') not in ('open','closed','upcoming','needs_review'):
            raise ValueError('Unknown application state')
        if x.get('status')!='open': continue
        if x.get('verification_status')!='verified' or x.get('official_source') is not True or not x.get('evidence','').strip():
            raise ValueError('Open call requires official evidence')
        checked=dt.datetime.fromisoformat(x['verified_at'].replace('Z','+00:00'))
        if checked.tzinfo is None or not dt.timedelta(0)<=now-checked<=dt.timedelta(days=7):
            raise ValueError('Stale or future verification')
        today=now.astimezone(dt.timezone(dt.timedelta(hours=8))).date() if x.get('deadline_timezone')=='Asia/Taipei' else now.date()
        if today<dt.date.fromisoformat(x['application_start']): raise ValueError('Not yet open')
        if x.get('deadline_precision')=='date':
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x['deadline']) or today>=dt.date.fromisoformat(x['deadline']):
                raise ValueError('Date-only deadline today or expired')
        else:
            deadline=dt.datetime.fromisoformat(x['deadline'].replace('Z','+00:00'))
            if deadline.tzinfo is None or now>=deadline: raise ValueError('Expired or timezone-less deadline')
        if x.get('source_id')=='ncaf' and (x.get('amount_status')!='verified_text' or not x.get('eligibility') or x.get('review_reasons')):
            raise ValueError('NCAF unresolved required facts')
        if x['type']=='residency':
            s=x.get('support',{})
            unresolved=r'待|未確認|unknown|不提供|沒有|自費|無(?:生活|津貼|藝術家費|製作|交通)|not provided|no (?:stipend|artist fee|production)|not available'
            known_cash=any(s.get(k) not in (None,False,'','unknown','待確認','無') and not re.search(unresolved,str(s.get(k)),re.I) for k in ('stipend','artist_fee','production','travel'))
            known_kind=any(s.get(k) is True or (re.search(r'免費|kostenlos|\bfree\b',str(s.get(k) or ''),re.I) and not re.search(unresolved+r'|非免費|不免費|not free|nicht kostenlos',str(s.get(k)),re.I)) for k in ('accommodation','studio'))
            if not all(k in s for k in ('stipend','artist_fee','accommodation','production','travel')) or not(known_cash or known_kind):
                raise ValueError('Residency requires verified cash funding or free accommodation/studio')
    return True
if __name__=='__main__':
    validate(json.loads((ROOT/'data/opportunities.json').read_text(encoding='utf-8')))
    print('Public data validation passed')
