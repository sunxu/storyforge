"""Safe aggregate performance instrumentation tests for R59 recovery."""
import unittest

from experiments.r58_quality.r59_gold192_history_recovery import RecoveryStageCursor


class FakeCursor:
    def __init__(self):
        self.rows = [{"safe": 1}, {"safe": 2}]
        self.one = None
        self.executed = 0

    def execute(self, query, params=None):
        self.executed += 1
        if str(query).startswith("EXPLAIN"):
            self.one = ([{
                "Plan": {
                    "Node Type": "Nested Loop",
                    "Plan Rows": 7,
                    "Total Cost": 12.5,
                    "Plans": [
                        {
                            "Node Type": "Index Only Scan",
                            "Index Name": "idx_v2_chat_message_ledger_r60_b2",
                            "Index Cond": (
                                "ROW(recorded_at, id) > "
                                "ROW(t.boundary_recorded_at, t.boundary_id)"
                            ),
                            "Plans": [],
                        },
                        {"Node Type": "Function Scan", "Plans": []},
                        {"Node Type": "Sort", "Plans": []},
                        {"Node Type": "Unique", "Plans": []},
                    ],
                }
            }],)
        return self

    def fetchone(self):
        return self.one

    def fetchall(self):
        return list(self.rows)


class RecoveryProfilerTests(unittest.TestCase):
    def test_target_ledger_query_captures_redacted_actual_parameter_plan(self):
        raw = FakeCursor()
        cursor = RecoveryStageCursor(raw)
        query = """
            WITH targets AS (SELECT 1)
            SELECT DISTINCT ON (e.message_id) e.id
            FROM public.v2_chat_message_ledger e
        """
        cursor.execute(query, ("private-story-id", "private-session-id"))
        rows = cursor.fetchall()
        metrics = cursor.safe_metrics()

        self.assertEqual(len(rows), 2)
        self.assertEqual(raw.executed, 4)  # SAVEPOINT, EXPLAIN, RELEASE, query
        self.assertEqual(len(metrics["query_plan_summaries"]), 1)
        plan = metrics["query_plan_summaries"][0]
        self.assertEqual(plan["plan_capture_status"], "CAPTURED")
        self.assertTrue(plan["b2_selected"])
        self.assertTrue(plan["index_only_scan"])
        self.assertTrue(plan["boundary_range_in_index_condition"])
        self.assertEqual(plan["sort_node_count"], 1)
        self.assertEqual(plan["unique_node_count"], 1)
        self.assertNotIn("private-story-id", str(metrics))
        self.assertNotIn("private-session-id", str(metrics))
        self.assertNotIn("ROW(recorded_at", str(metrics))

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
