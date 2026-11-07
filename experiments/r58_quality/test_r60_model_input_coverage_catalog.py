"""Synthetic catalog-only tests. No database or Gold192 source data accessed."""
import unittest

from experiments.r58_quality.r60_model_input_coverage_catalog import (
    COLUMNS,
    TABLES,
    classify,
)


class TestModelInputCoverageCatalog(unittest.TestCase):
    @staticmethod
    def fixtures(privileged=True, rls=True):
        return [
            (table, col, "text", rls, privileged, "synthetic_idx")
            for table in TABLES
            for col in COLUMNS[table]
        ]

    def test_complete_catalog_is_not_actual_coverage(self):
        result = classify(self.fixtures())
        self.assertEqual(set(result), set(TABLES))
        self.assertTrue(all(
            item["status"] == "CATALOG_READY_COUNTS_NOT_RUN"
            for item in result.values()
        ))
        self.assertTrue(all("synthetic_idx" in item["index_names"]
                            for item in result.values()))

    def test_missing_column_holds(self):
        fixtures = [
            row for row in self.fixtures()
            if not (row[0] == "v2_chat_reply_jobs" and row[1] == "request_envelope")
        ]
        out = classify(fixtures)
        self.assertEqual(out["v2_chat_reply_jobs"]["status"],
                         "SCHEMA_OR_PERMISSION_HOLD")
        self.assertIn("request_envelope",
                      out["v2_chat_reply_jobs"]["missing_expected_columns"])

    def test_no_privilege_or_no_rls_holds(self):
        for rows in (self.fixtures(privileged=False), self.fixtures(rls=False)):
            out = classify(rows)
            self.assertTrue(all(
                x["status"] == "SCHEMA_OR_PERMISSION_HOLD"
                for x in out.values()
            ))

    def test_absent_relation_holds(self):
        rows = [x for x in self.fixtures() if x[0] != "chat_latency_metrics"]
        result = classify(rows)
        self.assertEqual(result["chat_latency_metrics"]["status"], "CATALOG_ABSENT")


if __name__ == "__main__":
    unittest.main()
