"""Static validation for TFWR-vs-CPython language differences.

The validator uses Python's AST as a cheap front-end, then rejects constructs
that TFWR does not support and warns on a few high-value semantic mismatches.
This is intentionally conservative: it only reports issues that are clear from
syntax or from simple local type inference.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ValidationSeverity(StrEnum):
    """Severity levels emitted by the static validator."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    """A single static validation finding."""

    severity: ValidationSeverity
    code: str
    message: str
    line: int | None = None
    column: int | None = None
    path: Path | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "path": None if self.path is None else str(self.path),
        }

    def format(self) -> str:
        """Return a direct, location-aware diagnostic string."""
        location_parts: list[str] = []
        if self.path is not None:
            location_parts.append(str(self.path))
        if self.line is not None:
            location_parts.append(str(self.line))
        if self.column is not None:
            location_parts.append(str(self.column))

        location = ""
        if location_parts:
            location = ":".join(location_parts) + ": "

        return f"{location}{self.severity.value} {self.code}: {self.message}"


ALLOWED_METHODS_BY_TYPE = {
    "list": frozenset({"append", "insert", "pop", "remove"}),
    "dict": frozenset({"pop"}),
    "set": frozenset({"add", "remove"}),
    "str": frozenset(),
    "number": frozenset(),
    "tuple": frozenset(),
}


class _ValidationVisitor(ast.NodeVisitor):
    """AST visitor that records TFWR compatibility issues."""

    def __init__(self, *, path: Path | None = None) -> None:
        self.path = path
        self.issues: list[ValidationIssue] = []
        self._scope_stack: list[dict[str, str | None]] = [{}]

    def _push_scope(self) -> None:
        self._scope_stack.append({})

    def _pop_scope(self) -> None:
        self._scope_stack.pop()

    def _bind_name(self, name: str, kind: str | None) -> None:
        self._scope_stack[-1][name] = kind

    def _resolve_name(self, name: str) -> str | None:
        for scope in reversed(self._scope_stack):
            if name in scope:
                return scope[name]
        return None

    def _add_issue(
        self,
        node: ast.AST,
        *,
        severity: ValidationSeverity,
        code: str,
        message: str,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                severity=severity,
                code=code,
                message=message,
                line=getattr(node, "lineno", None),
                column=getattr(node, "col_offset", None),
                path=self.path,
            )
        )

    def _error(self, node: ast.AST, code: str, message: str) -> None:
        self._add_issue(node, severity=ValidationSeverity.ERROR, code=code, message=message)

    def _warning(self, node: ast.AST, code: str, message: str) -> None:
        self._add_issue(node, severity=ValidationSeverity.WARNING, code=code, message=message)

    def _expression_kind(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self._resolve_name(node.id)
        if isinstance(node, ast.List):
            return "list"
        if isinstance(node, ast.Dict):
            return "dict"
        if isinstance(node, ast.Set):
            return "set"
        if isinstance(node, ast.Tuple):
            return "tuple"
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return "str"
            if isinstance(node.value, (int, float, complex)) and not isinstance(node.value, bool):
                return "number"
            return None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"list", "dict", "set"} and not node.args and not node.keywords:
                return node.func.id
            if node.func.id == "str":
                return "str"
        return None

    def _index_value(self, node: ast.Subscript) -> ast.AST:
        return node.slice

    def _contains_fractional_behavior(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant):
            return isinstance(node.value, float) and not node.value.is_integer()
        if isinstance(node, ast.UnaryOp):
            return self._contains_fractional_behavior(node.operand)
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Div):
                return True
            return self._contains_fractional_behavior(node.left) or self._contains_fractional_behavior(
                node.right
            )
        return False

    def _warn_default_semantics(self, default: ast.AST) -> bool:
        if isinstance(default, ast.Constant):
            return False
        if isinstance(default, ast.Tuple):
            return any(self._warn_default_semantics(element) for element in default.elts)
        return True

    def _bind_assignment_target(self, target: ast.expr, value: ast.AST) -> None:
        inferred_kind = self._expression_kind(value)

        if isinstance(target, ast.Name):
            self._bind_name(target.id, inferred_kind)
            return

        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                if isinstance(element, ast.Name):
                    self._bind_name(element.id, None)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if node.args.vararg is not None:
            self._error(
                node.args.vararg,
                "varargs-not-supported",
                "TFWR does not support '*args'; spell out each parameter explicitly.",
            )
        if node.args.kwarg is not None:
            self._error(
                node.args.kwarg,
                "kwargs-not-supported",
                "TFWR does not support '**kwargs'; spell out each parameter explicitly.",
            )
        if node.args.kwonlyargs:
            self._error(
                node.args.kwonlyargs[0],
                "keyword-only-not-supported",
                "TFWR does not support keyword-only parameters; use positional parameters instead.",
            )

        for default in list(node.args.defaults) + [item for item in node.args.kw_defaults if item is not None]:
            if self._warn_default_semantics(default):
                self._warning(
                    default,
                    "default-binding-differs",
                    "Default expressions bind on call in TFWR; move runtime-dependent defaults into the function body.",
                )

        self._push_scope()
        for argument in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        ):
            self._bind_name(argument.arg, None)
        self.generic_visit(node)
        self._pop_scope()
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._error(
            node,
            "async-not-supported",
            "TFWR does not support async functions; rewrite this as synchronous control flow.",
        )
        self.generic_visit(node)
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._error(
            node,
            "class-not-supported",
            "TFWR does not support classes; use module-level functions and data structures instead.",
        )
        self.generic_visit(node)
        return None

    def visit_Lambda(self, node: ast.Lambda) -> Any:
        self._error(
            node,
            "lambda-not-supported",
            "TFWR does not support lambdas; define a named function instead.",
        )
        self.generic_visit(node)
        return None

    def visit_ListComp(self, node: ast.ListComp) -> Any:
        self._error(
            node,
            "list-comp-not-supported",
            "TFWR does not support list comprehensions; build the list with an explicit loop.",
        )
        self.generic_visit(node)
        return None

    def visit_SetComp(self, node: ast.SetComp) -> Any:
        self._error(
            node,
            "set-comp-not-supported",
            "TFWR does not support set comprehensions; build the set with an explicit loop.",
        )
        self.generic_visit(node)
        return None

    def visit_DictComp(self, node: ast.DictComp) -> Any:
        self._error(
            node,
            "dict-comp-not-supported",
            "TFWR does not support dict comprehensions; build the dict with explicit assignments.",
        )
        self.generic_visit(node)
        return None

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        self._error(
            node,
            "generator-exp-not-supported",
            "TFWR does not support generator expressions; use an explicit loop instead.",
        )
        self.generic_visit(node)
        return None

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        self._error(
            node,
            "ternary-not-supported",
            "TFWR does not support ternary expressions; expand this into an if/else block.",
        )
        self.generic_visit(node)
        return None

    def visit_Await(self, node: ast.Await) -> Any:
        self._error(
            node,
            "await-not-supported",
            "TFWR does not support 'await'; rewrite this as synchronous logic.",
        )
        self.generic_visit(node)
        return None

    def visit_Yield(self, node: ast.Yield) -> Any:
        self._error(
            node,
            "yield-not-supported",
            "TFWR does not support generators; return concrete values instead.",
        )
        self.generic_visit(node)
        return None

    def visit_YieldFrom(self, node: ast.YieldFrom) -> Any:
        self._error(
            node,
            "yield-from-not-supported",
            "TFWR does not support generators; expand this into explicit iteration.",
        )
        self.generic_visit(node)
        return None

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            self._bind_assignment_target(target, node.value)
        self.generic_visit(node)
        return None

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if node.value is not None:
            self._bind_assignment_target(node.target, node.value)
        self.generic_visit(node)
        return None

    def visit_For(self, node: ast.For) -> Any:
        if isinstance(node.target, ast.Name):
            self._bind_name(node.target.id, None)
        self.generic_visit(node)
        return None

    def visit_Call(self, node: ast.Call) -> Any:
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                self._error(
                    argument,
                    "starargs-not-supported",
                    "TFWR does not support '*args' calls; pass each argument explicitly.",
                )

        for keyword in node.keywords:
            if keyword.arg is None:
                self._error(
                    keyword,
                    "kwargs-not-supported",
                    "TFWR does not support '**kwargs' calls; pass arguments explicitly.",
                )
            else:
                self._error(
                    keyword,
                    "named-args-not-supported",
                    f"TFWR does not support named arguments like '{keyword.arg}='; pass this argument positionally.",
                )

        if isinstance(node.func, ast.Name) and node.func.id == "int":
            self._error(
                node,
                "int-not-supported",
                "TFWR does not support int(x); use x // 1 if you need floor-like behavior.",
            )

        if isinstance(node.func, ast.Attribute):
            receiver_kind = self._expression_kind(node.func.value)
            if receiver_kind in ALLOWED_METHODS_BY_TYPE:
                allowed_methods = ALLOWED_METHODS_BY_TYPE[receiver_kind]
                if node.func.attr not in allowed_methods:
                    self._error(
                        node,
                        "method-not-supported",
                        f"TFWR does not support '{receiver_kind}.{node.func.attr}()'; use supported methods or rewrite the logic explicitly.",
                    )

        self.generic_visit(node)
        return None

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        receiver_kind = self._expression_kind(node.value)
        if receiver_kind == "list" and self._contains_fractional_behavior(self._index_value(node)):
            self._warning(
                node,
                "list-index-rounding-differs",
                "TFWR rounds list indexes like 'lst[1.2]'; avoid fractional index expressions if exact Python-style indexing matters.",
            )
        self.generic_visit(node)
        return None

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if self._contains_fractional_behavior(node) and isinstance(
            node.op,
            (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow),
        ):
            self._warning(
                node,
                "float-only-number-semantics",
                "TFWR uses floats for all numbers; fractional arithmetic can accumulate rounding error differently than CPython integer-heavy code.",
            )
        self.generic_visit(node)
        return None


def has_blocking_issues(
    issues: list[ValidationIssue],
    *,
    strict_warnings: bool = False,
) -> bool:
    """Return whether the validator produced execution-blocking findings."""
    for issue in issues:
        if issue.severity == ValidationSeverity.ERROR:
            return True
        if strict_warnings and issue.severity == ValidationSeverity.WARNING:
            return True
    return False


def format_issues(
    issues: list[ValidationIssue],
    *,
    strict_warnings: bool = False,
) -> list[str]:
    """Return stable human-readable diagnostic lines."""
    lines = [issue.format() for issue in issues]
    if strict_warnings and any(issue.severity == ValidationSeverity.WARNING for issue in issues):
        lines.append("strict validation treats warnings as blocking issues.")
    return lines


def validate_source(text: str, path: Path | None = None) -> list[ValidationIssue]:
    """Validate a source string against known TFWR language differences."""
    issues: list[ValidationIssue] = []

    if not text.strip():
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="empty-source",
                message="source file is empty",
                path=path,
            )
        )
        return issues

    try:
        tree = ast.parse(text, filename="<unknown>" if path is None else str(path))
    except SyntaxError as exc:
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="python-syntax-error",
                message="Source does not parse as Python AST; fix the syntax before running the harness.",
                line=exc.lineno,
                column=exc.offset,
                path=path,
            )
        )
        return issues

    visitor = _ValidationVisitor(path=path)
    visitor.visit(tree)
    issues.extend(visitor.issues)

    return issues
