import datetime as dt
import unittest
from collect_ncaf import Document,demote
from adapter_cme import collect,official_datetime
from test_collect_ncaf import row,NOW
from validate_data import validate

HTML='''<eac-calls-detail title="Call for individual mobility 2026-2027" reference="Call for individual mobility 2026-2027" status="open" date-opening="1 October 2026, 9:00 CEST" date-deadline="30 April 2027, 23:59 CEST" date-extended-deadline="/">
legally residing in one of the Creative Europe countries; 18 years of age or older; design and fashion design; letter of invitation; another Creative Europe country. €85 per day of project implementation
</eac-calls-detail><li class="js-toggle-timeline-item"><div class="stripe-timeline-year">2026</div><a>31 October</a><a>30 November</a></li><li class="js-toggle-timeline-item"><div class="stripe-timeline-year">2027</div><a>30 April</a></li>'''
SOURCE={'id':'cme-test','name':'Fixture EU programme','url':'https://official.example/call','timezone':'Europe/Berlin'}
class Fake:
    def __init__(self,html=HTML):self.root=Document(html).root
    def html(self,url):return self.root
class MoreVerificationTests(unittest.TestCase):
    def test_rolling_dates_are_explicit_and_id_is_stable(self):
        a=collect(Fake(),SOURCE,NOW)[0][0]
        b=collect(Fake(),SOURCE,NOW+dt.timedelta(days=12))[0][0]
        self.assertEqual(a['deadline'],'2026-10-31');self.assertEqual(b['deadline'],'2026-11-30')
        self.assertEqual(a['id'],b['id']);self.assertEqual(a['status'],'open');self.assertEqual(a['daily_amount'],85)
        self.assertNotIn('funding_amount',a);self.assertTrue(validate({'opportunities':[a]},NOW))
    def test_rolling_cutoff_day_without_time_is_review_only(self):
        x=collect(Fake(),SOURCE,NOW+dt.timedelta(days=8))[0][0]
        self.assertEqual(x['deadline_precision'],'date');self.assertEqual(x['status'],'needs_review')
    def test_missing_year_and_conflicting_dst_labels_are_rejected(self):
        with self.assertRaises(ValueError):official_datetime('1 October, 9:00 CEST')
        with self.assertRaises(ValueError):official_datetime('1 January 2027, 9:00 CEST')
        with self.assertRaises(ValueError):collect(Fake(HTML.replace('date-opening=','unknown-opening=')),SOURCE,NOW)
    def test_explicit_closed_status_survives_fetch_failure(self):
        x=demote({'id':'closed-fixture','status':'closed'},NOW,'fetch failed')
        self.assertEqual(x['status'],'closed');self.assertEqual(x['verification_status'],'needs_review')
    def test_free_accommodation_qualifies_but_unknown_housing_does_not(self):
        x=row();x.update(type='residency',source_id='fixture',url='https://official.example/residency',support={'stipend':None,'artist_fee':None,'production':None,'travel':None,'accommodation':'免費住宿'})
        self.assertTrue(validate({'opportunities':[x]},NOW))
        for unknown in ('提供住宿，費用待核實','住宿非免費','not free','自費住宿'):
            x['support']['accommodation']=unknown
            with self.assertRaises(ValueError):validate({'opportunities':[x]},NOW)

if __name__=='__main__':unittest.main()
