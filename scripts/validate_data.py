"""Reject unsupported open claims before publication. Standard library only."""
import json,datetime,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
payload=json.loads((root/'data/opportunities.json').read_text(encoding='utf-8'))
assert isinstance(payload.get('opportunities'),list), 'opportunities must be an array'
now=datetime.datetime.now(datetime.timezone.utc)
for x in payload['opportunities']:
    assert isinstance(x,dict) and x.get('name') and x.get('type') in ('grant','residency')
    assert re.match(r'^https://',x.get('url','')), 'Official HTTPS URL required'
    if x.get('status')=='open':
        assert x.get('verification_status')=='verified' and x.get('official_source') is True
        assert x.get('evidence','').strip(), 'Official evidence required'
        for field in ('verified_at','deadline'):
            stamp=datetime.datetime.fromisoformat(x[field].replace('Z','+00:00'))
            assert stamp.tzinfo is not None, 'Timezone required'
            if field=='verified_at': assert datetime.timedelta(0)<=now-stamp<=datetime.timedelta(days=7), 'Stale verification'
            else: assert stamp>now, 'Expired open call'
        if x['type']=='residency':
            support=x.get('support',{})
            assert all(k in support for k in ('stipend','artist_fee','accommodation','production','travel'))
            assert any(v not in (None,False,'','unknown','待確認','無') for v in support.values()), 'Verified funding required'
print('Public data validation passed')
