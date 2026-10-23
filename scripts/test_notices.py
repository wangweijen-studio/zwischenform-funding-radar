import datetime as dt
import unittest
from official_notices import statement, apply_cached
from update_all import reconcile
from test_cme import Fake, SOURCE, HTML, collect

NOW=dt.datetime(2026,10,23,10,tzinfo=dt.timezone.utc)

class NoticeTests(unittest.TestCase):
    def test_explicit_and_conditional_notices(self):
        self.assertIsNotNone(statement('This call has been cancelled.'))
        self.assertIsNone(statement('If this call is cancelled, applicants will be notified.'))
        self.assertIsNone(statement('本次徵件尚未取消。'))

    def test_round_scope_must_be_in_the_notice(self):
        client=type('Client',(),{'cache':{'https://official.example/p':b'<main>115 round 6. This call has been cancelled.</main>'}})()
        record={'url':'https://official.example/p','name':'Programme · 115 round 6','record_kind':'program_round'}
        result=apply_cached([record],client,NOW)[0]
        self.assertEqual(result['status'],'needs_review')
        client.cache[record['url']]=b'<main>115 round 6: this call has been cancelled.</main>'
        self.assertEqual(apply_cached([record],client,NOW)[0]['status'],'cancelled')

    def test_cancellation_survives_missing_notice(self):
        previous={'id':'one','name':'Call','url':'https://official.example/p','status':'cancelled','cancellation_evidence':'This call has been cancelled'}
        fresh={'id':'one','name':'Call','url':previous['url'],'status':'open','verification_status':'verified'}
        self.assertEqual(reconcile([previous],[fresh],[],NOW)[0][0]['status'],'cancelled')

    def test_semantic_eu_cancellation(self):
        result=collect(Fake(HTML.replace('status="open"','status="cancelled"')),SOURCE,NOW)[0][0]
        self.assertEqual(result['status'],'cancelled')

