"""Regression cases for extraction, status, deduplication and failed refreshes."""
import datetime as dt
import unittest
from unittest.mock import patch
from collect_ncaf import Document, canonical, date_ranges, make_record, collect, demote, news_range, relevant, match_program
from validate_data import validate

NOW = dt.datetime(2026, 10, 23, 8, 0, tzinfo=dt.timezone.utc)
URL = 'https://www.ncafroc.org.tw/founding_detail.html?sid=46'
PROGRAM = {'name': '各類別國際文化交流(出國)', 'url': URL}
HTML = '''<div id="foundingD1"><p>視覺藝術展覽</p></div>
<div id="foundingD2"><div class="applyTime"><div class="period">115年 第6期</div>
<div class="part"><div class="label">收件時間</div><div class="time">2026/10/16-2026/11/16</div></div>
<div class="part"><div class="label">計畫執行起始時間</div><div class="time">2027/01/01</div></div></div></div>
<div id="foundingD4"><p>申請資格：具有中華民國國籍之自然人、持永久居留證之外籍人士。</p></div>
<!-- <div class="applyTime">bogus template example</div> -->'''
FACTS = {'rules_year_matches': True, 'cutoff_time': '23:59', 'amount': '依必要機票費核定', 'rules_url': URL}


def row(now=NOW, facts=None):
    root = Document(HTML).root
    return make_record(PROGRAM, root, date_ranges(root)[0], now, FACTS if facts is None else facts)


class ExtractionTests(unittest.TestCase):
    def test_longest_program_name_wins(self):
        programs = [{'name': '視覺藝術'}, {'name': '視覺藝術策展專案'}, {'name': '視覺藝術組織營運補助專案'}]
        self.assertEqual(match_program(programs, '116年度視覺藝術組織營運專案受理申請')['name'], '視覺藝術組織營運補助專案')

    def test_only_receipt_dates_not_project_start(self):
        values = date_ranges(Document(HTML).root)
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0][1], dt.date(2026, 11, 16))

    def test_year_not_inferred_from_roc_budget_year(self):
        self.assertIsNone(news_range('116年度專案，11月1日至30日受理申請'))
        self.assertEqual(news_range('自2026年11月1日至30日開放線上申請')[1], dt.date(2026, 11, 30))

    def test_official_url_canonicalization(self):
        self.assertEqual(canonical(URL + '&utm_source=x#foo'), URL)
        self.assertTrue(canonical('/news_detail.html?id=abcdef').endswith('?id=abcdef'))
        with self.assertRaises(ValueError):
            canonical('https://www.ncafroc.org.tw.evil.example/call')

    def test_open_round_verified_by_complete_evidence(self):
        r = row()
        self.assertEqual(r['status'], 'open')
        self.assertTrue(validate({'opportunities': [r]}, NOW))
        self.assertEqual(r['deadline'], '2026-11-16T23:59:00+08:00')

    def test_future_round_not_open(self):
        self.assertEqual(row(NOW - dt.timedelta(days=20))['status'], 'upcoming')

    def test_expired_round_not_open(self):
        self.assertEqual(row(NOW + dt.timedelta(days=40))['status'], 'closed')

    def test_missing_amount_or_wrong_rules_year_requires_review(self):
        for f in ({}, {**FACTS, 'amount': None}, {**FACTS, 'rules_year_matches': False}):
            self.assertEqual(row(facts=f)['status'], 'needs_review')

    def test_date_only_cutoff_day_is_not_open(self):
        f = {**FACTS, 'cutoff_time': None}
        r = row(dt.datetime(2026, 11, 16, tzinfo=dt.timezone.utc), f)
        self.assertEqual(r['status'], 'needs_review')
        self.assertEqual(r['deadline'], '2026-11-16')

    def test_failed_refresh_retains_verification_timestamp_but_demotes(self):
        old = row()
        r = demote(old, NOW + dt.timedelta(days=1), 'HTTP failed')
        self.assertEqual(r['verified_at'], old['verified_at'])
        self.assertEqual(r['verification_status'], 'needs_review')

    def test_validation_rejects_duplicate_future_expired_stale(self):
        r = row()
        with self.assertRaises(ValueError):
            validate({'opportunities': [r, r]}, NOW)
        for change in ({'application_start': '2027-01-01'}, {'deadline': '2026-10-01T23:59:00+08:00'},
                       {'verified_at': '2026-10-01T00:00:00+00:00'}, {'url': 'https://evil.example/call'}):
            with self.assertRaises(ValueError):
                validate({'opportunities': [{**r, **change}]}, NOW)

    def test_result_notice_excluded_and_duplicate_program_deduplicated(self):
        index = '<div class="foundingCard"><a href="founding_detail.html?sid=46"><div class="name">各類別國際文化交流(出國)</div></a></div>'
        news = '<div class="newsCard"><a href="news_detail.html?sid=1"><div class="title">國際文化交流補助名單公布</div></a></div>'
        class FakeFetch:
            requests = []
            def html(self, url):
                if 'founding.aspx' in url:
                    return Document(index + index).root
                return Document(news if 'news.html' in url else HTML).root
        with patch('collect_ncaf.pdf_facts', return_value=FACTS):
            rows, status = collect(FakeFetch(), [row()], NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(status['news_excluded'], 1)
        self.assertEqual(status['announcements_checked'], 0)

    def test_unrelated_arts_areas_not_added_by_generic_art_word(self):
        self.assertFalse(relevant('長篇小說創作發表專案'))
        self.assertTrue(relevant('多元藝術'))


if __name__ == '__main__':
    unittest.main()
