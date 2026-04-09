# * Importer tests

import pytest

from bank_analyzer import importer

# ** canonicalize_description
def test_no_whitespace_unchanged():
    assert importer.canonicalize_description('aqq') == 'aqq'

def test_empty_string_unchanged():
    assert importer.canonicalize_description('') == ''

def test_blank_string_collapsed():
    assert importer.canonicalize_description('  \t\n') == ''

def test_normal_string_unchanged():
    assert importer.canonicalize_description('aqq bum') == 'aqq bum'

def test_leading_whitespace_stripped():
    assert importer.canonicalize_description(' \taqq') == 'aqq'

def test_trailing_whitespace_stripped():
    assert importer.canonicalize_description('aqq\n') == 'aqq'

def test_whitespace_collapsed():
    assert importer.canonicalize_description('  aqq\t bum\n\n   \tbęc\t\n') == 'aqq bum bęc'
