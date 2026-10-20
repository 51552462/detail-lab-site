import csv
import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook
from pipeline import Store, DataError, FIELDS


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root, 'SYN-A')
        self.store.add_metric('SYN-A', 'SITE1', 'CONTACTS', 'v1', '건', '같은 날 유효 문의 건수, 테스트 정의')
        self.row = ['r1', 'SITE1', 'CONTACTS', 'v1', '2026-10-01', '10.5']

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def csv(self, rows=None, headers=None):
        path = self.root / 'sample.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as target:
            writer = csv.writer(target)
            writer.writerow(headers or FIELDS)
            writer.writerows(rows if rows is not None else [self.row])
        return path

    def ingest(self, path=None, tenant='SYN-A'):
        return self.store.ingest(tenant, 'SRC1', path or self.csv(), 'synthetic-fixture', '2026-10-01', '2026-10-31')

    def test_approval_required_and_provenance_retained(self):
        result = self.ingest()
        with self.assertRaisesRegex(DataError, 'LATEST_SOURCE_NOT_APPROVED'):
            self.store.report('SYN-A', 'SRC1')
        self.store.review('SYN-A', 'SRC1', result['version'], 'reviewer')
        report = self.store.report('SYN-A', 'SRC1')
        self.assertEqual(report['records'][0]['value'], '10.5')
        self.assertEqual(report['records'][0]['unit'], '건')
        self.assertEqual(report['source']['period_start'], '2026-10-01')
        self.assertEqual(len(report['source']['sha256']), 64)
        self.assertEqual(report['state'], 'draft')

    def test_duplicate_is_idempotent(self):
        self.ingest(); result = self.ingest()
        self.assertTrue(result['duplicate'])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM sources').fetchone()[0], 1)

    def test_changed_file_requires_new_approval(self):
        self.ingest(); self.store.review('SYN-A', 'SRC1', 1, 'reviewer')
        self.row[-1] = '11'
        self.assertEqual(self.ingest()['version'], 2)
        with self.assertRaisesRegex(DataError, 'LATEST_SOURCE_NOT_APPROVED'):
            self.store.report('SYN-A', 'SRC1')
        self.assertEqual(self.store.db.execute("SELECT state FROM sources WHERE version=1").fetchone()[0], 'approved')

    def test_same_bytes_changed_metadata_creates_version(self):
        path = self.csv(); self.ingest(path)
        result = self.store.ingest('SYN-A', 'SRC1', path, 'new-test-origin', '2026-10-01', '2026-10-31')
        self.assertEqual(result['version'], 2)

    def test_cross_tenant_read_write_review_blocked(self):
        for action in [lambda: self.ingest(tenant='SYN-B'), lambda: self.store.report('SYN-B', 'SRC1'),
                       lambda: self.store.review('SYN-B', 'SRC1', 1, 'reviewer')]:
            with self.assertRaisesRegex(DataError, 'TENANT_MISMATCH'):
                action()

    def test_separate_tenant_database_has_no_other_data(self):
        self.ingest()
        other = Store(self.root, 'SYN-B')
        try:
            self.assertEqual(other.db.execute('SELECT COUNT(*) FROM sources').fetchone()[0], 0)
        finally:
            other.close()

    def test_real_customer_ids_blocked(self):
        with self.assertRaisesRegex(DataError, 'SYNTHETIC_ONLY'):
            Store(self.root, 'CLIENT-real')

    def test_extra_sensitive_column_rejected(self):
        with self.assertRaisesRegex(DataError, 'HEADER_MISMATCH'):
            self.ingest(self.csv([self.row + ['not-allowed']], FIELDS + ['email']))

    def test_invalid_row_rolls_back_entire_file(self):
        bad = self.row.copy(); bad[0] = 'r2'; bad[4] = '2026-10-02'; bad[-1] = 'NaN'
        with self.assertRaisesRegex(DataError, 'INVALID_VALUE:ROW_3'):
            self.ingest(self.csv([self.row, bad]))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM sources').fetchone()[0], 0)

    def test_duplicate_point_rejected(self):
        row2 = self.row.copy(); row2[0] = 'r2'
        with self.assertRaisesRegex(DataError, 'DUPLICATE_ROW'):
            self.ingest(self.csv([self.row, row2]))

    def test_unknown_definition_and_outside_period_rejected(self):
        self.row[3] = 'v99'
        with self.assertRaisesRegex(DataError, 'UNKNOWN_METRIC_OR_SITE'):
            self.ingest()
        self.row[3] = 'v1'; self.row[4] = '2026-09-30'
        with self.assertRaisesRegex(DataError, 'OUTSIDE_PERIOD'):
            self.ingest()

    def test_xlsx_and_formula_rejection(self):
        book = Workbook(); sheet = book.active
        sheet.append(FIELDS); sheet.append(self.row)
        path = self.root / 'sample.xlsx'; book.save(path)
        self.assertEqual(self.ingest(path)['rows'], 1)
        sheet['F2'] = '=1+2'; book.save(path)
        with self.assertRaisesRegex(DataError, 'FORMULA_REJECTED'):
            self.ingest(path)

    def test_rejected_source_not_reported(self):
        self.ingest(); self.store.review('SYN-A', 'SRC1', 1, 'reviewer', approve=False)
        with self.assertRaisesRegex(DataError, 'LATEST_SOURCE_NOT_APPROVED'):
            self.store.report('SYN-A', 'SRC1')


if __name__ == '__main__':
    unittest.main()
