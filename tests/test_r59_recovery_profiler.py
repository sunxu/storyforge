"""Safe aggregate performance instrumentation tests for R59 recovery."""
import unittest

from experiments.r58_quality.r59_gold192_history_recovery import RecoveryStageCursor


class FakeCursor:
    def __init__(self):
        self.rows = [{"safe": 1}, {"safe": 2}]
        self.executed = 0

    def execute(self, query, params=None):
        self.executed += 1
        return self

    def fetchall(self):
        return list(self.rows)


class RecoveryProfilerTests(unittest.TestCase):
    def test_metrics_count_queries_and_rows_without_retaining_sql_or_params(self):
        raw = FakeCursor()
        cursor = RecoveryStageCursor(raw)
        cursor.execute("SELECT 1 FROM public.v2_chat_messages WHERE id = %s", ("private-id",))
        rows = cursor.fetchall()
        metrics = cursor.safe_metrics()

        self.assertEqual(len(rows), 2)
        self.assertEqual(raw.executed, 1)
        self.assertEqual(metrics["total_query_count"], 1)
        self.assertEqual(metrics["total_rows_fetched"], 2)
        self.assertTrue(metrics["sql_text_retained"] is False)
        self.assertTrue(metrics["sql_parameters_retained"] is False)
        self.assertEqual(
            sum(v["query_count"] for v in metrics["query_classes"].values()), 1
        )
        self.assertEqual(
            sum(v["rows_fetched"] for v in metrics["query_classes"].values()), 2
        )


if __name__ == "__main__":
    unittest.main()
