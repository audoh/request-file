from abc import ABC, abstractmethod
from os import path
from subprocess import PIPE, run
from typing import Generator, List, Set, Tuple

import pytest
from _pytest.mark.structures import MarkDecorator
from py.path import local

from tests.conftest import args


def completer(*, cword: int, words: List[str], cwd: str) -> Set[str]:
    if not isinstance(cword, int):
        raise TypeError("cword must be an int")
    if not isinstance(words, list):
        raise TypeError("words must be a list")
    _path = path.normpath(path.join(path.dirname(__file__), "../bin/bash-completer.sh"))
    res = run([_path, str(cword), *words], cwd=cwd, stdout=PIPE, stderr=PIPE)
    raw = res.stdout.decode("utf-8")
    _list = raw.splitlines()
    assert all(
        (_list.index(value) == index for value, index in zip(_list, range(len(_list))))
    ), "items should not be duplicated"
    return set(_list)


class BaseTestCase(ABC):
    @abstractmethod
    def prepare(self, tmpdir: local) -> None:
        raise NotImplementedError

    def run(
        self,
        tmpdir: local,
        cword: int,
        words_before: List[str],
        word: str,
        words_after: List[str],
        result: Set[str],
    ) -> None:
        _dir = tmpdir.mkdir("tmp")
        self.prepare(tmpdir=_dir)
        assert (
            completer(
                cword=cword, words=[*words_before, word, *words_after], cwd=_dir.strpath
            )
            == result
        )

    @staticmethod
    def parametrize(*params: Tuple[str, Set[str]]) -> MarkDecorator:
        return pytest.mark.parametrize(
            ("word", "result"),
            list(params),
            ids=[f"""> $=\"{param[0]}\"""" for param in params],
        )

    @staticmethod
    def parametrize_context() -> MarkDecorator:
        values = [
            (0, [], []),
            (0, [], ["word"]),
            (1, ["word"], []),
            (1, ["word1"], ["word2"]),
        ]
        return pytest.mark.parametrize(
            ("cword", "words_before", "words_after"),
            values,
            ids=[
                f"""{value[0]} {" ".join(value[1])} $ {" ".join(value[2])} """
                for value in values
            ],
        )

    @staticmethod
    def get_trick_word(word: str) -> str:
        return f"{word}asdf"


class TestEmptyDir(BaseTestCase):
    def prepare(self, tmpdir: local) -> None:
        return

    @BaseTestCase.parametrize(
        ("", args()),
        ("-", args("-")),
        ("--", args("--")),
        ("--he", args("--help")),
        ("--help", args("--help")),
    )
    @BaseTestCase.parametrize_context()
    def test(
        self,
        tmpdir: local,
        cword: int,
        words_before: List[str],
        word: str,
        words_after: List[str],
        result: Set[str],
    ) -> None:
        self.run(
            tmpdir=tmpdir,
            cword=cword,
            words_before=words_before,
            word=word,
            words_after=words_after,
            result=result,
        )


class TestOneDir(BaseTestCase):
    def prepare(self, tmpdir: local) -> None:
        tmpdir.mkdir("one")

    @BaseTestCase.parametrize(
        ("", {*args(), "one/"}),
        ("-", args("-")),
        ("--", args("--")),
        ("--he", args("--help")),
        ("--help", args("--help")),
        ("t", set()),
        ("o", {"one/", BaseTestCase.get_trick_word("one/")}),
        ("one", {"one/", BaseTestCase.get_trick_word("one/")}),
        ("one/", set()),
    )
    @BaseTestCase.parametrize_context()
    def test(
        self,
        tmpdir: local,
        cword: int,
        words_before: List[str],
        word: str,
        words_after: List[str],
        result: Set[str],
    ) -> None:
        self.run(
            tmpdir=tmpdir,
            cword=cword,
            words_before=words_before,
            word=word,
            words_after=words_after,
            result=result,
        )


class TestTwoDirs(BaseTestCase):
    def prepare(self, tmpdir: local) -> None:
        tmpdir.mkdir("one")
        tmpdir.mkdir("other")

    @BaseTestCase.parametrize(
        ("", {*args(), "one/", "other/"}),
        ("-", args("-")),
        ("--", args("--")),
        ("--he", args("--help")),
        ("--help", args("--help")),
        ("t", set()),
        ("o", {"one/", "other/"}),
        ("one", {"one/", BaseTestCase.get_trick_word("one/")}),
        ("other", {"other/", BaseTestCase.get_trick_word("other/")}),
        ("one/", set()),
        ("other/", set()),
    )
    @BaseTestCase.parametrize_context()
    def test(
        self,
        tmpdir: local,
        cword: int,
        words_before: List[str],
        word: str,
        words_after: List[str],
        result: Set[str],
    ) -> None:
        self.run(
            tmpdir=tmpdir,
            cword=cword,
            words_before=words_before,
            word=word,
            words_after=words_after,
            result=result,
        )


class TestOneFile(BaseTestCase):
    def prepare(self, tmpdir: local) -> None:
        with open(tmpdir.join("one.json"), "w") as fp:
            fp.write("{}")

    @BaseTestCase.parametrize(
        ("", {*args(), "one.json"}),
        ("-", args("-")),
        ("--", args("--")),
        ("--he", args("--help")),
        ("--help", args("--help")),
        ("t", set()),
        ("o", {"one.json"}),
        ("one", {"one.json"}),
        ("one.json", {"one.json"}),
    )
    @BaseTestCase.parametrize_context()
    def test(
        self,
        tmpdir: local,
        cword: int,
        words_before: List[str],
        word: str,
        words_after: List[str],
        result: Set[str],
    ) -> None:
        self.run(
            tmpdir=tmpdir,
            cword=cword,
            words_before=words_before,
            word=word,
            words_after=words_after,
            result=result,
        )


class TestTwoDirsOneFile(BaseTestCase):
    def prepare(self, tmpdir: local) -> None:
        tmpdir.mkdir("one")
        tmpdir.mkdir("other")
        with open(tmpdir.join("one.json"), "w") as fp:
            fp.write("{}")

    @BaseTestCase.parametrize(
        ("", {*args(), "one/", "other/", "one.json"}),
        ("-", args("-")),
        ("--", args("--")),
        ("--he", args("--help")),
        ("--help", args("--help")),
        ("t", set()),
        ("o", {"one/", "other/", "one.json"}),
        ("one", {"one/", "one.json"}),
        ("other", {"other/", BaseTestCase.get_trick_word("other/")}),
        ("one/", set()),
        ("other/", set()),
        ("one.json", {"one.json"}),
    )
    @BaseTestCase.parametrize_context()
    def test(
        self,
        tmpdir: local,
        cword: int,
        words_before: List[str],
        word: str,
        words_after: List[str],
        result: Set[str],
    ) -> None:
        self.run(
            tmpdir=tmpdir,
            cword=cword,
            words_before=words_before,
            word=word,
            words_after=words_after,
            result=result,
        )
