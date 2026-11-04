from __future__ import annotations

import unittest

from scripts.hf_job_guard import (
    PolicyError,
    build_hf_argv,
    parse_volume,
    validate_spec,
)

INPUT = (
    "hf://buckets/adradar/storyforge-training/"
    "preflight/r59/input.jsonl:/input/input.jsonl:ro"
)
SCRIPT = (
    "hf://buckets/adradar/storyforge-training/"
    "scripts/worker.py:/scripts/worker.py:ro"
)
OUTPUT = (
    "hf://buckets/adradar/storyforge-training/"
    "preflight/r59/reports/attempt-2:/output:rw"
)


class HuggingFaceJobGuardTests(unittest.TestCase):
    def valid(self, **overrides):
        values = {
            "namespace": "adradar",
            "flavor": "cpu-basic",
            "timeout_minutes": 15,
            "input_volumes": [INPUT, SCRIPT],
            "output_volume": OUTPUT,
            "command": ["python3", "/scripts/worker.py"],
        }
        values.update(overrides)
        return validate_spec(**values)

    def test_valid_ro_inputs_and_separate_rw_output(self):
        inputs, output = self.valid()
        self.assertEqual([item.mode for item in inputs], ["ro", "ro"])
        self.assertEqual(output.mode, "rw")
        self.assertEqual(output.destination, "/output")

    def test_directory_prefix_mounts_are_allowed(self):
        inputs, output = self.valid(
            input_volumes=[
                "hf://buckets/adradar/storyforge-training/"
                "preflight/r59/20261103:/input:ro",
                "hf://buckets/adradar/storyforge-training/"
                "scripts/r59-context-window-20261104-a62b247:/scripts:ro",
            ],
        )
        self.assertEqual([v.destination for v in inputs], ["/input", "/scripts"])
        self.assertEqual(output.destination, "/output")

    def test_similar_non_root_destinations_are_rejected(self):
        for bad in ("/inputs", "/scripts-old", "/input-other"):
            with self.subTest(destination=bad):
                with self.assertRaisesRegex(
                    PolicyError, "INPUT_DESTINATION_MUST_BE_INPUT_OR_SCRIPTS"
                ):
                    self.valid(
                        input_volumes=[
                            "hf://buckets/adradar/storyforge-training/"
                            "preflight/r59/20261103:" + bad + ":ro",
                        ],
                    )

    def test_personal_namespace_fallback_rejected(self):
        with self.assertRaisesRegex(PolicyError, "NAMESPACE_MUST_BE_ADRADAR"):
            self.valid(namespace="greenkeedle")

    def test_rw_input_mount_rejected(self):
        with self.assertRaisesRegex(PolicyError, "INPUT_MUST_BE_READ_ONLY"):
            self.valid(input_volumes=[INPUT.replace(":ro", ":rw")])

    def test_missing_rw_output_rejected(self):
        with self.assertRaisesRegex(PolicyError, "SEPARATE_READ_WRITE_OUTPUT_REQUIRED"):
            self.valid(output_volume=OUTPUT.replace(":rw", ":ro"))

    def test_gpu_flavor_rejected(self):
        with self.assertRaisesRegex(PolicyError, "GPU_ESCALATION_FORBIDDEN"):
            self.valid(flavor="a100-large")

    def test_cpu_timeout_is_bounded(self):
        with self.assertRaisesRegex(PolicyError, "CPU_TIMEOUT_OUT_OF_RANGE"):
            self.valid(timeout_minutes=121)

    def test_bucket_escape_rejected(self):
        with self.assertRaisesRegex(PolicyError, "VOLUME_OUTSIDE_PROJECT_BUCKET"):
            parse_volume("hf://buckets/other/private/file:/input/file:ro")

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(PolicyError, "VOLUME_SOURCE_PATH_INVALID"):
            parse_volume(
                "hf://buckets/adradar/storyforge-training/a/../secret:/input/file:ro"
            )

    def test_input_output_source_prefix_overlap_rejected(self):
        nested_output = (
            "hf://buckets/adradar/storyforge-training/"
            "preflight/r59/input.jsonl/reports:/output:rw"
        )
        with self.assertRaisesRegex(PolicyError, "INPUT_OUTPUT_SOURCE_COLLISION"):
            self.valid(output_volume=nested_output)

    def test_duplicate_destinations_rejected(self):
        with self.assertRaisesRegex(PolicyError, "DUPLICATE_INPUT_DESTINATION"):
            self.valid(input_volumes=[INPUT, INPUT])

    def test_submit_argv_pins_namespace_and_no_retry(self):
        argv = build_hf_argv(
            namespace="adradar",
            name="r59-cpu-check",
            flavor="cpu-basic",
            timeout_minutes=15,
            input_volumes=[INPUT, SCRIPT],
            output_volume=OUTPUT,
            image="python:3.11",
            command=["python3", "/scripts/worker.py"],
        )
        self.assertIn("--namespace", argv)
        self.assertEqual(argv[argv.index("--namespace") + 1], "adradar")
        self.assertEqual(argv[argv.index("--attempts") + 1], "1")
        self.assertEqual(argv.count("-v"), 3)
        self.assertIn("--", argv)


if __name__ == "__main__":
    unittest.main()
