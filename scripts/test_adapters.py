import datetime as dt
import unittest
from unittest.mock import patch
from urllib.robotparser import RobotFileParser
from collect_ncaf import Document
from official_http import OfficialHTTP,Blocked
from adapter_fonds import collect as fonds
from adapter_solitude import collect as solitude
from adapter_moc import collect as moc
from update_all import reconcile

NOW=dt.datetime(2026,10,23,10,tzinfo=dt.timezone.utc)
SOURCE={'id':'fonds','name':'Fonds','url':'https://example.org/program','timezone':'Europe/Berlin'}
class Fake:
    def __init__(self,html):self.root=Document(html).root
    def html(self,url):return self.root
class AdapterTests(unittest.TestCase):
    def test_recurring_dates_do_not_prove_current_round(self):
        rows,_,_=fonds(Fake('Allgemeine Projektförderung 2. Oktober bis 2. November'),SOURCE,NOW)
        self.assertEqual(rows[0]['status'],'needs_review');self.assertIsNone(rows[0]['deadline'])
    def test_dated_round_and_organization_restriction(self):
        html='Allgemeine Projektförderung Nächstmögliche Antragstellung: 2. Okt - 2. Nov 2026 mind. 5.000 Euro und max. 30.000 Euro mindestens drei natürliche Personen mit Wohnsitz in Deutschland Einzelpersonen Ausstellungen ohne Partizipation 23.59 Uhr'
        row=fonds(Fake(html),SOURCE,NOW)[0][0]
        self.assertEqual(row['status'],'open');self.assertEqual(row['funding_amount'],30000)
        self.assertTrue(row['deadline'].endswith('+01:00'));self.assertIn('不可單獨',row['eligibility'])
        self.assertEqual(fonds(Fake(html),SOURCE,NOW+dt.timedelta(days=20))[0][0]['status'],'closed')
    def test_residency_money_does_not_prove_open(self):
        html='Solitude Fellowship A monthly fellowship of €1,300 from around the world 6- or 9-month'
        x=solitude(Fake(html),SOURCE,NOW)[0][0]
        self.assertEqual(x['status'],'needs_review');self.assertEqual(x['monthly_amount'],1300);self.assertNotIn('funding_amount',x)
    def test_moc_blocked_detail_not_verified(self):
        html='<main><a href="https://grants.moc.gov.tw/Web/Normal.jsp?id=1">藝術出版補助，自115年10月1日至115年11月13日受理申請</a></main>'
        rows,errors,_=moc(Fake(html),SOURCE,NOW)
        self.assertTrue(errors);self.assertEqual(rows[0]['status'],'needs_review');self.assertIsNone(rows[0]['verified_at'])
    def test_robots_denial_never_fetches_body(self):
        c=OfficialHTTP(['example.org']);r=RobotFileParser();r.parse(['User-agent: *','Disallow: /']);c.robots['example.org']=r
        with patch.object(c,'raw') as raw:
            with self.assertRaises(Blocked):c.get('https://example.org/call')
            raw.assert_not_called()
    def test_http_official_domain_and_credentials(self):
        c=OfficialHTTP(['example.org'])
        for url in ['http://example.org/','https://example.org.evil/','https://user:pass@example.org/','https://example.org:444/']:
            with self.assertRaises(Blocked):c.allowed_url(url)
    def test_deadline_change_keeps_deployed_ncaf_id(self):
        old={'id':'old','source_id':'ncaf','url':'https://example.org/','name':'Art · Round 1','record_kind':'program_round','deadline':'2026-10-25'}
        fresh={**old,'id':'new','deadline':'2026-11-01'}
        rows,history=reconcile([old],[fresh],[],NOW)
        self.assertEqual(rows[0]['id'],'old');self.assertEqual(history[0]['field'],'deadline')

if __name__=='__main__':unittest.main()
