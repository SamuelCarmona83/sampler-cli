from sampler.indexer.imports import extract_imports


def test_extract_python_imports() -> None:
    content = """
import os
import myproject.utils
from myproject.core import helper
from . import sibling
"""
    modules = extract_imports(content, "python")
    assert "os" in modules
    assert "myproject.utils" in modules
    assert "myproject.core" in modules


def test_extract_go_imports() -> None:
    content = """
package main

import (
    "fmt"
    "github.com/acme/widgets"
)

import "errors"
"""
    modules = extract_imports(content, "go")
    assert "fmt" in modules
    assert "github.com/acme/widgets" in modules
    assert "errors" in modules


def test_extract_typescript_imports() -> None:
    content = """
import { add } from './utils';
import express from 'express';
export { helper } from '../shared/helper';
const x = require('lodash');
"""
    modules = extract_imports(content, "typescript")
    assert "./utils" in modules
    assert "express" in modules
    assert "../shared/helper" in modules
    assert "lodash" in modules


def test_extract_imports_unknown_language_returns_empty() -> None:
    assert extract_imports("anything", "cobol") == []
