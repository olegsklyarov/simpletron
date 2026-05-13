#!/usr/bin/env python3
"""
Запускает тесты из подкаталогов tests/: для каждого каталога с src.txt
выполняет кейсы 01..99 с парами NN.in / NN.out.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


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
    failures: list[tuple[str, str, str, str, int | None, str]] = []

    for test_dir in sorted(tests_root.iterdir(), key=lambda p: p.name):
        if not test_dir.is_dir() or test_dir.name.startswith("."):
            continue

        src = test_dir / "src.txt"
        if not src.is_file():
            continue

        src_arg = str(src.resolve())

        for n in range(1, 100):
            nn = f"{n:02d}"
            path_in = test_dir / f"{nn}.in"
            path_out = test_dir / f"{nn}.out"
            if not path_in.is_file() or not path_out.is_file():
                continue

            path_run = test_dir / f"{nn}.run"
            label = f"{test_dir.name}/{nn}"

            total += 1
            with open(path_in, "rb") as fin, open(path_run, "wb") as fout_run:
                proc = subprocess.run(
                    [str(simpletron), src_arg],
                    cwd=str(repo_root),
                    stdin=fin,
                    stdout=fout_run,
                    stderr=subprocess.PIPE,
                )

            expected = read_text(path_out)
            actual = read_text(path_run)
            ok = proc.returncode == 0 and expected == actual

            if ok:
                passed += 1
            else:
                stderr_txt = proc.stderr.decode("utf-8", errors="replace")
                failures.append(
                    (label, str(path_out), str(path_run), expected, proc.returncode, stderr_txt)
                )

    print(f"Запущено тестов: {total}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {total - passed}")

    if args.verbose and failures:
        print()
        for label, p_exp, p_act, expected, code, stderr_txt in failures:
            print(f"Провален: {label}")
            if code is not None and code != 0:
                print(f"  код выхода: {code}")
            if stderr_txt.strip():
                print("  stderr:")
                for line in stderr_txt.rstrip().splitlines():
                    print(f"    {line}")
            print(f"  ожидаемо ({p_exp}):")
            for line in expected.splitlines(keepends=True):
                print(f"    {line}", end="" if line.endswith("\n") else "\n")
            if expected and not expected.endswith("\n"):
                print()
            print(f"  фактически ({p_act}):")
            actual = read_text(Path(p_act))
            for line in actual.splitlines(keepends=True):
                print(f"    {line}", end="" if line.endswith("\n") else "\n")
            if actual and not actual.endswith("\n"):
                print()
            print()

    return 0 if total == passed else 1


if __name__ == "__main__":
    sys.exit(main())
