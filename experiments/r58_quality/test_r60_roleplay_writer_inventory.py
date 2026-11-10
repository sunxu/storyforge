"""Synthetic-only tests for the read-only RolePlay T1 inventory scanner."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.r58_quality import r60_roleplay_writer_inventory as inventory


class RolePlayWriterInventoryTest(unittest.TestCase):
    def test_detect_sql_writes_functions_and_trigger_candidates(self):
        source = """
CREATE OR REPLACE FUNCTION public.bind_v2_legacy_retry_source()
RETURNS void AS $$
UPDATE public.v2_chat_messages SET metadata = '{}'::jsonb;
DELETE FROM public.v2_chat_messages WHERE id IS NULL;
$$ LANGUAGE plpgsql;
CREATE TRIGGER capture_v2_chat_message_ledger
AFTER INSERT OR UPDATE OR DELETE ON public.v2_chat_messages
FOR EACH ROW EXECUTE FUNCTION public.capture_v2_chat_message_ledger();
"""
        results = inventory.capture("supabase/migrations/demo.sql", source)
        self.assertEqual(
            {r["operation"] for r in results if r["kind"] == "SQL_MESSAGE_WRITE"},
            {"UPDATE", "DELETE_FROM"},
        )
        self.assertIn(
            "bind_v2_legacy_retry_source",
            {r["function"] for r in results if r["kind"] == "SQL_FUNCTION_DEFINITION"},
        )

    def test_detect_typescript_and_rpc_metadata_only(self):
        source = """
const userSecret = "PRIVATE_SHOULD_NEVER_BE_EMITTED";
const result = await supabaseAdmin
  .from('v2_chat_messages')
  .update({status: "failed"})
  .eq("id", id);
const bind = await supabaseAdmin.rpc('bind_v2_legacy_retry_source', {});
"""
        results = inventory.capture("src/lib/db/example.ts", source)
        self.assertTrue(any(r["kind"] == "SUPABASE_MESSAGE_TABLE"
                            and "UPDATE" in r["operations_candidate"] for r in results))
        self.assertTrue(any(r["kind"] == "RPC_CALL_CANDIDATE"
                            and r["function"] == "bind_v2_legacy_retry_source"
                            for r in results))
        self.assertNotIn("PRIVATE_SHOULD_NEVER_BE_EMITTED", repr(results))

    def test_reject_unverified_repository_before_reading_files(self):
        with tempfile.TemporaryDirectory() as base:
            path = Path(base)
            with patch.object(inventory, "git", side_effect=[
                (str(path) + "\n").encode(),
                b"origin https://github.com/example/not-our-project.git (fetch)\n",
            ]), self.assertRaisesRegex(ValueError, "ROLEPLAY_REMOTE_NOT_VERIFIED"):
                inventory.run(path)


if __name__ == "__main__":
    unittest.main()
