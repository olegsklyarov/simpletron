#!/usr/bin/env python3
"""
Запускает тесты из подкаталогов tests/: для каждого каталога с src.txt
выполняет кейсы 01..99 с парами NN.in / NN.out (и опционально NN.err, NN.exit).
Кейс NN.expect_timeout: ожидается, что процесс не завершится за 5 с (таймаут).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


RUN_TIMEOUT_SEC = 5


@dataclass
class TestFailure:
    label: str
    reason: str
    path_exp_out: Path | None = None
    path_act_out: Path | None = None
    path_exp_err: Path | None = None
    expected_out: bytes = b""
    actual_out: bytes = b""
    expected_err: bytes = b""
    actual_err: bytes = b""
    expected_code: int | None = None
    actual_code: int | None = None
    stderr_txt: str = ""


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def read_exit_code(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return int(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Тестирование simpletron по наборам в tests/<имя>/"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Подробности по проваленным тестам (ожидаемый и фактический вывод)",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=Path("tests"),
        help="Корень с тестовыми каталогами (по умолчанию: tests)",
    )
    parser.add_argument(
        "--simpletron",
        type=Path,
        default=Path("./simpletron"),
        help="Исполняемый файл simpletron (по умолчанию: ./simpletron)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    tests_root = (repo_root / args.tests_dir).resolve()
    simpletron = (repo_root / args.simpletron).resolve()

    if not simpletron.is_file():
        print(
            f"Ошибка: не найден {simpletron}. Соберите проект: make",
            file=sys.stderr,
        )
        return 2

    if not tests_root.is_dir():
        print(f"Ошибка: каталог тестов не найден: {tests_root}", file=sys.stderr)
        return 2

    total = 0
    passed = 0
    failures: list[TestFailure] = []

    for test_dir in sorted(tests_root.iterdir(), key=lambda p: p.name):
        if not test_dir.is_dir() or test_dir.name.startswith("."):
            continue

        src = test_dir / "src.txt"
        if not src.is_file():
            continue

        src_arg = str(src.resolve())

        for n in range(1, 100):
            nn = f"{n:02d}"
            label = f"{test_dir.name}/{nn}"

            path_expect_timeout = test_dir / f"{nn}.expect_timeout"
            path_in = test_dir / f"{nn}.in"
            path_out = test_dir / f"{nn}.out"
            path_err = test_dir / f"{nn}.err"
            path_exit = test_dir / f"{nn}.exit"
            path_run = test_dir / f"{nn}.run"
            path_run_err = test_dir / f"{nn}.run.err"

            if path_expect_timeout.is_file():
                if not path_in.is_file():
                    continue

                total += 1
                try:
                    with open(path_in, "rb") as fin, open(path_run, "wb") as fout_run:
                        proc = subprocess.run(
                            [str(simpletron), src_arg],
                            cwd=str(repo_root),
                            stdin=fin,
                            stdout=fout_run,
                            stderr=subprocess.PIPE,
                            timeout=RUN_TIMEOUT_SEC,
                        )
                except subprocess.TimeoutExpired:
                    passed += 1
                    continue

                stderr_txt = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
                failures.append(
                    TestFailure(
                        label=label,
                        reason="ожидался таймаут (бесконечный цикл), процесс завершился",
                        actual_code=proc.returncode,
                        stderr_txt=stderr_txt,
                    )
                )
                continue

            if not path_in.is_file() or not path_out.is_file():
                continue

            total += 1
            expected_out = read_bytes(path_out)
            expected_err = read_bytes(path_err) if path_err.is_file() else b""
            expected_code = read_exit_code(path_exit) if path_exit.is_file() else 0

            try:
                with open(path_in, "rb") as fin, open(path_run, "wb") as fout_run:
                    proc = subprocess.run(
                        [str(simpletron), src_arg],
                        cwd=str(repo_root),
                        stdin=fin,
                        stdout=fout_run,
                        stderr=subprocess.PIPE,
                        timeout=RUN_TIMEOUT_SEC,
                    )
            except subprocess.TimeoutExpired:
                failures.append(
                    TestFailure(
                        label=label,
                        reason=f"таймаут {RUN_TIMEOUT_SEC} с",
                        path_exp_out=path_out,
                        path_act_out=path_run,
                        path_exp_err=path_err if path_err.is_file() else None,
                        expected_out=expected_out,
                        expected_err=expected_err,
                        expected_code=expected_code,
                    )
                )
                continue

            actual_out = read_bytes(path_run)
            actual_err = proc.stderr if proc.stderr is not None else b""
            path_run_err.write_bytes(actual_err)

            ok_out = actual_out == expected_out
            ok_err = actual_err == expected_err
            ok_code = proc.returncode == expected_code
            ok = ok_out and ok_err and ok_code

            if ok:
                passed += 1
            else:
                parts: list[str] = []
                if not ok_out:
                    parts.append("stdout")
                if not ok_err:
                    parts.append("stderr")
                if not ok_code:
                    parts.append("код возврата")
                reason = "несовпадение: " + ", ".join(parts)
                failures.append(
                    TestFailure(
                        label=label,
                        reason=reason,
                        path_exp_out=path_out,
                        path_act_out=path_run,
                        path_exp_err=path_err if path_err.is_file() else None,
                        expected_out=expected_out,
                        actual_out=actual_out,
                        expected_err=expected_err,
                        actual_err=actual_err,
                        expected_code=expected_code,
                        actual_code=proc.returncode,
                        stderr_txt=actual_err.decode("utf-8", errors="replace"),
                    )
                )

    print(f"Запущено тестов: {total}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {total - passed}")

    if args.verbose and failures:
        print()
        for fobj in failures:
            print(f"Провален: {fobj.label} ({fobj.reason})")
            if fobj.stderr_txt.strip():
                print("  stderr процесса:")
                for line in fobj.stderr_txt.rstrip().splitlines():
                    print(f"    {line}")
            if fobj.expected_code is not None or fobj.actual_code is not None:
                print(
                    f"  код возврата: ожидалось {fobj.expected_code!r}, "
                    f"получено {fobj.actual_code!r}"
                )
            if fobj.path_exp_out is not None:
                print(f"  stdout ожидаемо ({fobj.path_exp_out}):")
                _print_bytes_block(fobj.expected_out)
                print(f"  stdout фактически ({fobj.path_act_out}):")
                _print_bytes_block(fobj.actual_out)
            if fobj.path_exp_err is not None or fobj.expected_err or fobj.actual_err:
                print(f"  stderr ожидаемо ({fobj.path_exp_err}):")
                _print_bytes_block(fobj.expected_err)
                print("  stderr фактически (из pipe):")
                _print_bytes_block(fobj.actual_err)
            print()

    return 0 if total == passed else 1


def _print_bytes_block(data: bytes) -> None:
    if not data:
        print("    <пусто>")
        return
    text = data.decode("utf-8", errors="replace")
    for line in text.splitlines(keepends=True):
        print(f"    {line}", end="" if line.endswith("\n") else "\n")
    if text and not text.endswith("\n"):
        print()


if __name__ == "__main__":
    sys.exit(main())
