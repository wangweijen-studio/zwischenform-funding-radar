import datetime as dt
import unittest
from collect_ncaf import Document,demote
from adapter_global_residency import collect
NOW=dt.datetime(2026,10,23,10,tzinfo=dt.timezone.utc)
class Fake:
    def __init__(self,text):self.text=text
    def html(self,url):return Document('<main>'+self.text+'</main>').root
def source(key):return {'id':key,'name':'Fixture official','url':'https://official.example/','programme_name':'Fixture residency','residency_adapter':key,'geographic_region':'outside_europe'}
class ResidencyAdapterTests(unittest.TestCase):
    def test_proof_schema_requires_source_and_time_even_when_call_closed(self):
        from validate_residency_policy import validate_policy
        row={'type':'residency','status':'closed','residency_policy':{'region':'europe','components':{'studio':{'status':'confirmed'}},'airfare':{'coverage':'unknown'}}}
        with self.assertRaises(ValueError):validate_policy(row)
    def test_airfare_cap_cannot_omit_currency(self):
        from validate_residency_policy import validate_policy
        with self.assertRaises(ValueError):validate_policy({'type':'residency','residency_policy':{'region':'outside_europe','airfare':{'coverage':'partial','cap':500}}})
    def test_berlin_departure_cannot_be_marked_without_its_own_rule(self):
        from validate_residency_policy import validate_policy
        with self.assertRaises(ValueError):validate_policy({'type':'residency','residency_policy':{'region':'outside_europe','airfare':{'coverage':'round_trip_full','berlin_eligible':True}}})
    def test_invalid_region_is_not_assumed_to_be_europe(self):
        from validate_residency_policy import validate_policy
        with self.assertRaises(ValueError):validate_policy({'type':'residency','residency_policy':{'region':'International'}})
    def test_empty_semantic_main_does_not_hide_real_funded_programme(self):
        class Page:
            def html(self,url):return Document('<main></main><article>Artist-in-Residence Program Provisions A private studio, accommodation, transportation, production fee, living expense</article>').root
        rows,_,_=collect(Page(),source('arcus'),NOW)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['residency_policy']['components']['stipend']['status'],'confirmed')
    def test_international_sam_airfare_does_not_prove_berlin_or_nationality(self):
        text='A fully funded programme, SAM Residencies 1 x return airfare on economy class Monthly stipend of SGD$1,500 Housing allowance for foreign residents A studio space OR co-working space open to those based in Singapore or internationally'
        row=collect(Fake(text),source('sam'),NOW)[0][0];p=row['residency_policy']
        self.assertEqual(p['airfare']['coverage'],'round_trip_full');self.assertFalse(p['airfare']['berlin_eligible']);self.assertEqual(p['eligibility']['nationality']['status'],'needs_review');self.assertEqual(p['eligibility']['residence']['status'],'eligible')
    def test_pure_paid_or_wrong_programme_cannot_enter_funded_list(self):
        with self.assertRaises(ValueError):collect(Fake('ARCUS Research self-funded program fee JPY270000'),source('arcus'),NOW)
    def test_bundanon_explicit_self_funded_travel_is_not_airfare_support(self):
        text='providing residencies free of charge most artists are provided with a private room Artists in Residence Complex expenses, including travel, food, toiletries, and materials from Australia and overseas'
        row=collect(Fake(text),source('bundanon'),NOW)[0][0];p=row['residency_policy']
        self.assertEqual(p['components']['airfare']['status'],'not_provided');self.assertEqual(p['airfare']['coverage'],'none');self.assertEqual(p['components']['accommodation']['status'],'confirmed')
    def test_stale_data_demotion_carries_failed_profile_without_modifying_original(self):
        original={'id':'r','status':'needs_review','residency_policy':{'checked_at':'old'}}
        row=demote(original,NOW,'failed')
        self.assertEqual(row['residency_policy']['fetch_status'],'failed');self.assertNotIn('fetch_status',original['residency_policy'])
    def test_us_only_stipend_does_not_prove_cash_support_for_berlin_artist(self):
        text='US-based artists-in-residence receive a $1,250 USD monthly stipend and $750 USD travel stipend. What items are provided in my live/work studio? private kitchen and bathroom'
        rows,errors,meta=collect(Fake(text),source('bemis'),NOW)
        self.assertFalse(rows);self.assertFalse(errors);self.assertEqual(meta['excluded_unverified'],1)
