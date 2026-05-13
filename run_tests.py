#!/usr/bin/env python3
"""
Запускает тесты: все файлы *.stest под --tests-dir (рекурсивно).
Каждый кейс — один файл в формате секций (как phpt): программа, stdin и ожидания.
Файлы могут лежать прямо в tests/ (например divide-01.stest) или в подкаталогах.
В любой строке допускается хвостовой комментарий: пробел/таб, затем # и до конца строки.

Секция — строка --имя-- (строчные латинские буквы, цифры, дефисы), тело до
следующей строки --...-- или EOF. Секция --program-- записывается во временный
файл, его путь передаётся simpletron; после прогона файл удаляется.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


RUN_TIMEOUT_SEC = 1

SECTION_HEADER = re.compile(r"^--([a-z0-9-]+)--\s*$")
# Хвостовой комментарий: пробел/таб + # … до конца строки (не трогаем # в начале тела без пробела перед ним).
STEST_LINE_COMMENT = re.compile(r"\s+#.*$")


def strip_stest_line_comment(line: str) -> str:
    """Убирает из строки stest хвостовой комментарий ` # ...` (тело строки сохраняется с переводом строки)."""
    if line.endswith("\r\n"):
        body, suffix = line[:-2], "\r\n"
    elif line.endswith("\n"):
        body, suffix = line[:-1], "\n"
    elif line.endswith("\r"):
        body, suffix = line[:-1], "\r"
    else:
        body, suffix = line, ""
    body = STEST_LINE_COMMENT.sub("", body).rstrip(" \t")
    return body + suffix


@dataclass
class TestFailure:
    label: str
    reason: str
    path_stest: Path | None = None
    path_act_out: Path | None = None
    path_exp_err: Path | None = None
    expected_out: bytes = b""
    actual_out: bytes = b""
    expected_err: bytes = b""
    actual_err: bytes = b""
    expected_code: int | None = None
    actual_code: int | None = None
    stderr_txt: str = ""


def parse_sections(text: str) -> dict[str, str]:
    """Разбор секций: значения — строки как в файле (с переводами строк)."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    for line in text.splitlines(keepends=True):
        line = strip_stest_line_comment(line)
        bare = line.rstrip("\r\n")
        m = SECTION_HEADER.fullmatch(bare)
        if m is not None:
            if current is not None:
                sections[current] = "".join(buf)
            current = m.group(1)
            buf = []
            continue
        if current is None:
            raise ValueError("содержимое до первой секции --имя-- недопустимо")
        buf.append(line)

    if current is None:
        raise ValueError("нет ни одной секции")
    sections[current] = "".join(buf)
    return sections


def load_stest(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8")
    return parse_sections(raw)


def section_bytes(sections: dict[str, str], name: str) -> bytes:
    return sections.get(name, "").encode("utf-8")


def parse_expect_exit(sections: dict[str, str]) -> int:
    if "expect-exit" not in sections:
        return 0
    t = sections["expect-exit"].strip()
    if not t:
        return 0
    return int(t.splitlines()[0].strip(), 10)


@contextmanager
def program_as_temp_file(program: str):
    """Записывает текст программы во временный файл и удаляет его после блока."""
    fd, name = tempfile.mkstemp(prefix="simpletron_", suffix=".txt")
    try:
        os.write(fd, program.encode("utf-8"))
    finally:
        os.close(fd)
    path = Path(name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Тестирование simpletron по файлам *.stest (рекурсивно)"
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
        help="Корень с тестами (по умолчанию: tests); ищутся все *.stest ниже",
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

    stest_files = sorted(
        tests_root.rglob("*.stest"),
        key=lambda p: (str(p.parent), p.name),
    )

    total = 0
    passed = 0
    failures: list[TestFailure] = []

    for path_stest in stest_files:
        if any(part.startswith(".") for part in path_stest.relative_to(tests_root).parts):
            continue

        label = str(path_stest.relative_to(tests_root))
        stem = path_stest.stem
        test_dir = path_stest.parent
        path_run = test_dir / f"{stem}.run"
        path_run_err = test_dir / f"{stem}.run.err"

        try:
            sections = load_stest(path_stest)
        except (ValueError, OSError, UnicodeDecodeError) as e:
            print(f"Ошибка разбора {path_stest}: {e}", file=sys.stderr)
            return 2

        if "program" not in sections:
            print(
                f"Ошибка: в {path_stest} нет секции --program--",
                file=sys.stderr,
            )
            return 2

        if "stdin" not in sections:
            print(
                f"Ошибка: в {path_stest} нет секции --stdin--",
                file=sys.stderr,
            )
            return 2

        stdin_b = section_bytes(sections, "stdin")
        expect_timeout = "expect-timeout" in sections

        if expect_timeout:
            total += 1
            try:
                with program_as_temp_file(sections["program"]) as prog_path:
                    try:
                        proc = subprocess.run(
                            [str(simpletron), str(prog_path.resolve())],
                            cwd=str(repo_root),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            input=stdin_b,
                            timeout=RUN_TIMEOUT_SEC,
                        )
                    except subprocess.TimeoutExpired:
                        passed += 1
                        continue

                    stderr_txt = (
                        proc.stderr.decode("utf-8", errors="replace")
                        if proc.stderr
                        else ""
                    )
                    failures.append(
                        TestFailure(
                            label=label,
                            reason="ожидался таймаут (бесконечный цикл), процесс завершился",
                            path_stest=path_stest,
                            actual_code=proc.returncode,
                            stderr_txt=stderr_txt,
                        )
                    )
            except OSError as e:
                print(f"Ошибка временного файла для {path_stest}: {e}", file=sys.stderr)
                return 2
            continue

        if "expect-stdout" not in sections:
            print(
                f"Ошибка: в {path_stest} нет секции --expect-stdout-- "
                "(или добавьте --expect-timeout--)",
                file=sys.stderr,
            )
            return 2

        expected_out = section_bytes(sections, "expect-stdout")
        expected_err = section_bytes(sections, "expect-stderr")
        expected_code = parse_expect_exit(sections)

        total += 1
        try:
            with program_as_temp_file(sections["program"]) as prog_path:
                try:
                    proc = subprocess.run(
                        [str(simpletron), str(prog_path.resolve())],
                        cwd=str(repo_root),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        input=stdin_b,
                        timeout=RUN_TIMEOUT_SEC,
                    )
                except subprocess.TimeoutExpired:
                    failures.append(
                        TestFailure(
                            label=label,
                            reason=f"таймаут {RUN_TIMEOUT_SEC} с",
                            path_stest=path_stest,
                            path_act_out=path_run,
                            path_exp_err=path_stest if expected_err else None,
                            expected_out=expected_out,
                            expected_err=expected_err,
                            expected_code=expected_code,
                        )
                    )
                    continue

                actual_out = proc.stdout if proc.stdout is not None else b""
                actual_err = proc.stderr if proc.stderr is not None else b""
                path_run.write_bytes(actual_out)
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
                            path_stest=path_stest,
                            path_act_out=path_run,
                            path_exp_err=path_stest if expected_err else None,
                            expected_out=expected_out,
                            actual_out=actual_out,
                            expected_err=expected_err,
                            actual_err=actual_err,
                            expected_code=expected_code,
                            actual_code=proc.returncode,
                            stderr_txt=actual_err.decode("utf-8", errors="replace"),
                        )
                    )
        except OSError as e:
            print(f"Ошибка временного файла для {path_stest}: {e}", file=sys.stderr)
            return 2

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
            if fobj.path_act_out is not None:
                print(f"  stdout ожидаемо (секция --expect-stdout-- в {fobj.path_stest}):")
                _print_bytes_block(fobj.expected_out)
                print(f"  stdout фактически ({fobj.path_act_out}):")
                _print_bytes_block(fobj.actual_out)
            if fobj.expected_err or fobj.actual_err:
                print(f"  stderr ожидаемо (секция --expect-stderr-- в {fobj.path_stest}):")
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
