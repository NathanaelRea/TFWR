from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[2]


class HarnessCliTests(unittest.TestCase):
    def test_module_entrypoint_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tfwr_harness", "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode)
        self.assertIn("run-scenario", result.stdout)
        self.assertIn("describe-scenario", result.stdout)
        self.assertIn("normalize-trace", result.stdout)
        self.assertIn("list-presets", result.stdout)
        self.assertIn("validate", result.stdout)

    def test_validate_subcommand_returns_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tfwr_harness", "validate", "leader_reset.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("[]", result.stdout.strip())

    def test_validate_subcommand_returns_nonzero_for_blocking_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "bad.py"
            script_path.write_text("value = lambda x: x\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-m", "tfwr_harness", "validate", str(script_path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn('"code": "lambda-not-supported"', result.stdout)

    def test_validate_subcommand_strict_mode_blocks_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "warn.py"
            script_path.write_text("values = [0, 1]\nitem = values[1.2]\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-m", "tfwr_harness", "validate", "--strict", str(script_path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn('"code": "list-index-rounding-differs"', result.stdout)

    def test_describe_scenario_returns_normalized_summary(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tfwr_harness",
                "describe-scenario",
                "tests/scenarios/example_reset.json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode)
        self.assertIn('"name": "example-fastest-reset"', result.stdout)
        self.assertIn('"mode": "leaderboard"', result.stdout)
        self.assertIn('"preset": "fastest-reset"', result.stdout)
        self.assertIn('"script_path":', result.stdout)

    def test_run_scenario_returns_json_summary(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tfwr_harness",
                "run-scenario",
                "tests/scenarios/example_carrot.json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode)
        self.assertIn('"scenario_name": "example-carrot-entrypoint"', result.stdout)
        self.assertIn('"success": true', result.stdout)
        self.assertIn('"final_state":', result.stdout)

    def test_run_scenario_failure_includes_recent_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "broken.py"
            manifest_path = Path(tmpdir) / "broken.json"
            script_path.write_text("from __builtins__ import *\nraise ValueError('boom')\n", encoding="utf-8")
            manifest_path.write_text(
                "{\n"
                '  "name": "broken",\n'
                f'  "script_path": "{script_path}",\n'
                '  "mode": "normal"\n'
                "}\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tfwr_harness",
                    "run-scenario",
                    str(manifest_path),
                    "--recent-events",
                    "2",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn('"failure_context":', result.stdout)
        self.assertIn('"recent_events":', result.stdout)
        self.assertIn('"run_failed"', result.stdout)

    def test_normalize_trace_subcommand_returns_json_and_can_write_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            capture_path = Path(tmpdir) / "output.txt"
            output_path = Path(tmpdir) / "normalized.json"
            capture_path.write_text("200 checkpoint speed 1 180\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tfwr_harness",
                    "normalize-trace",
                    str(capture_path),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            written = output_path.read_text(encoding="utf-8")

        self.assertEqual(0, result.returncode)
        self.assertIn('"tick": 200', result.stdout)
        self.assertIn('"checkpoint"', result.stdout)
        self.assertEqual(result.stdout.strip(), written.strip())

    def test_normalize_trace_subcommand_returns_harness_error_for_malformed_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            capture_path = Path(tmpdir) / "broken.txt"
            capture_path.write_text('"unterminated\n', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tfwr_harness",
                    "normalize-trace",
                    str(capture_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode)
        self.assertIn("invalid capture text for normalization", result.stderr)

    def test_list_presets_subcommand_lists_known_presets(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tfwr_harness", "list-presets"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode)
        self.assertIn('"name": "fastest-reset"', result.stdout)
        self.assertIn('"name": "fastest-reset-smoke"', result.stdout)


if __name__ == "__main__":
    unittest.main()
