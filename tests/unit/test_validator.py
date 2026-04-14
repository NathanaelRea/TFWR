from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tfwr_harness.models import GameState, RunStatus, Scenario
from tfwr_harness.runtime import HarnessRuntime, RuntimeOptions
from tfwr_harness.validator import (
    ValidationSeverity,
    format_issues,
    has_blocking_issues,
    validate_source,
)


class ValidatorTests(unittest.TestCase):
    def test_rejects_core_unsupported_tfwr_constructs(self) -> None:
        source = textwrap.dedent(
            """
            class Bad:
                pass

            value = lambda x: x
            data = [item for item in range(3)]
            other = 1 if True else 0

            def fn(*args, **kwargs):
                return args

            fn(value=1)
            """
        )

        issues = validate_source(source, path=Path("bad.py"))
        codes = {issue.code for issue in issues if issue.severity == ValidationSeverity.ERROR}

        self.assertIn("class-not-supported", codes)
        self.assertIn("lambda-not-supported", codes)
        self.assertIn("list-comp-not-supported", codes)
        self.assertIn("ternary-not-supported", codes)
        self.assertIn("varargs-not-supported", codes)
        self.assertIn("kwargs-not-supported", codes)
        self.assertIn("named-args-not-supported", codes)
        self.assertTrue(has_blocking_issues(issues))

    def test_rejects_unsupported_methods_on_known_builtin_types(self) -> None:
        source = textwrap.dedent(
            """
            values = []
            mapping = {}
            text = " crop "
            count = 3

            values.sort()
            mapping.keys()
            text.strip()
            count.bit_length()
            """
        )

        issues = validate_source(source, path=Path("methods.py"))
        error_messages = "\n".join(format_issues(issues))

        self.assertIn("list.sort()", error_messages)
        self.assertIn("dict.keys()", error_messages)
        self.assertIn("str.strip()", error_messages)
        self.assertIn("number.bit_length()", error_messages)

    def test_warns_on_default_binding_fractional_numbers_and_fractional_list_indexes(self) -> None:
        source = textwrap.dedent(
            """
            values = [0, 1, 2]

            def read_now(x=get_pos_x()):
                return x

            item = values[1.2]
            ratio = 0.1 + 0.2
            """
        )

        issues = validate_source(source, path=Path("warn.py"))
        codes = [issue.code for issue in issues if issue.severity == ValidationSeverity.WARNING]

        self.assertIn("default-binding-differs", codes)
        self.assertIn("list-index-rounding-differs", codes)
        self.assertIn("float-only-number-semantics", codes)
        self.assertFalse(has_blocking_issues(issues))
        self.assertTrue(has_blocking_issues(issues, strict_warnings=True))

    def test_formats_location_aware_diagnostics(self) -> None:
        issues = validate_source("value = lambda x: x\n", path=Path("script.py"))

        formatted = format_issues(issues)

        self.assertEqual(1, len(formatted))
        self.assertIn("script.py:1:8:", formatted[0])
        self.assertIn("lambda-not-supported", formatted[0])

    def test_reports_python_syntax_errors(self) -> None:
        issues = validate_source("def broken(:\n    pass\n", path=Path("broken.py"))

        self.assertEqual(ValidationSeverity.ERROR, issues[0].severity)
        self.assertEqual("python-syntax-error", issues[0].code)
        self.assertTrue(has_blocking_issues(issues))


class RuntimeValidationTests(unittest.TestCase):
    def test_runtime_blocks_invalid_root_script_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script_path = root / "bad.py"
            script_path.write_text("value = lambda x: x\n", encoding="utf-8")

            runtime = HarnessRuntime()
            result = runtime.run(
                Scenario(
                    name="invalid-root",
                    script_path=script_path,
                    initial_state=GameState(world_size=1),
                )
            )

        self.assertEqual(RunStatus.FAILED, result.status)
        self.assertFalse(result.success)
        self.assertTrue(any("lambda-not-supported" in line for line in result.errors))

    def test_runtime_blocks_invalid_imported_module_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "helper.py").write_text("value = lambda x: x\n", encoding="utf-8")
            (root / "main.py").write_text("import helper\n", encoding="utf-8")

            runtime = HarnessRuntime()
            result = runtime.run(
                Scenario(
                    name="invalid-import",
                    script_path=root / "main.py",
                    initial_state=GameState(world_size=1),
                )
            )

        self.assertEqual(RunStatus.FAILED, result.status)
        self.assertFalse(result.success)
        self.assertTrue(any("helper.py" in line for line in result.errors))

    def test_runtime_strict_validation_promotes_warnings_to_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script_path = root / "warn.py"
            script_path.write_text(
                textwrap.dedent(
                    """
                    values = [0, 1]
                    item = values[1.2]
                    """
                ),
                encoding="utf-8",
            )

            runtime = HarnessRuntime(options=RuntimeOptions(strict_validation=True))
            result = runtime.run(
                Scenario(
                    name="strict-warning",
                    script_path=script_path,
                    initial_state=GameState(world_size=1),
                )
            )

        self.assertEqual(RunStatus.FAILED, result.status)
        self.assertTrue(any("strict validation treats warnings" in line for line in result.errors))


if __name__ == "__main__":
    unittest.main()
