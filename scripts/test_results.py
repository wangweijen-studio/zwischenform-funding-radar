import datetime as dt
import unittest
from collect_ncaf import Document
from official_results import result_proof,collect_results
NOW=dt.datetime(2026,10,23,12,tzinfo=dt.timezone.utc)
URL='https://www.berlin.de/result'
class ResultTests(unittest.TestCase):
    def test_programme_year_is_not_its_submission_deadline_year(self):
        from adapter_berlin import collect
        class Fake:
            hosts={'www.berlin.de'}
            def html(self,url):return Document('<main>Abgabe-/ Bewerbungsfrist: 22. Oktober 2026 Voraussetzungen Antragstellende müssen in Berlin leben. Umfang der Förderung Haushaltsmittel für das Jahr 2027. Zeitraum der Ausschreibung</main>').root
        row=collect(Fake(),{'id':'berlin-kultur','name':'Official culture office','url':'https://www.berlin.de/sen/kultur/foerderung/'},NOW)[0][-1]
        self.assertEqual(row['funding_year'],'2027');self.assertEqual(row['deadline'],'2026-10-22');self.assertIn('Berlin',row['eligibility'])
    def proof(self,html):return result_proof(Document(html).root,URL,2027,NOW)
    def test_other_year_with_current_year_in_navigation_is_rejected(self):
        self.assertIsNone(self.proof('<nav>IMPACT 2027</nav><main><h1>IMPACT Juryentscheidung 2026</h1><time datetime="2026-10-20"></time></main>'))
    def test_date_and_year_specific_result_are_required(self):
        self.assertIsNone(self.proof('<main><h1>IMPACT Juryentscheidung 2027</h1></main>'))
        self.assertIsNone(self.proof('<main><h1>IMPACT Förderung 2027</h1><time datetime="2026-10-20"></time></main>'))
    def test_result_proof_carries_date_link_document_and_verification(self):
        proof=self.proof('<main><h1>IMPACT Juryentscheidung 2027</h1><time datetime="2026-10-20"></time><a href="/list.pdf">Liste</a></main>')
        self.assertTrue(proof['verified']);self.assertEqual(proof['published_at'],'2026-10-20');self.assertEqual(proof['document_urls'],['https://www.berlin.de/list.pdf'])
    def test_future_or_conflicting_dates_are_not_claimed_as_published(self):
        for dates in ['<time datetime="2027-01-01"></time>','<time datetime="2026-10-20"></time><time datetime="2026-10-21"></time>']:
            self.assertIsNone(self.proof('<main><h1>IMPACT Ergebnis 2027</h1>'+dates+'</main>'))
    def test_missing_body_proof_stays_pending(self):
        class Fake:
            def html(self,url):return Document('<main><h1>IMPACT Ergebnis 2026</h1><p>2027</p></main>').root
        root=Document('<main><a href="/result">IMPACT Ergebnis 2027</a></main>').root
        verified,pending,errors=collect_results(Fake(),root,URL,NOW)
        self.assertFalse(verified);self.assertEqual(pending,[URL]);self.assertFalse(errors)
