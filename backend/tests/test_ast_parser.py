from pathlib import Path
import pytest
from repollama.engines.ast_parser import ASTParser, UnsupportedLanguageError


def test_language_detection():
    parser = ASTParser()
    assert parser.get_language_from_extension(".py") == "python"
    assert parser.get_language_from_extension("PY") == "python"
    assert parser.get_language_from_extension(".js") == "javascript"
    assert parser.get_language_from_extension(".jsx") == "javascript"
    assert parser.get_language_from_extension(".ts") == "typescript"
    assert parser.get_language_from_extension(".tsx") == "tsx"
    assert parser.get_language_from_extension(".txt") is None


def test_unsupported_language_error():
    parser = ASTParser()
    with pytest.raises(UnsupportedLanguageError):
        parser.parse_content(b"console.log(1);", "unsupported_lang")


def test_parse_python_content():
    parser = ASTParser()
    code = b"""
import os
from sys import path

class DataManager:
    def __init__(self, value: int):
        self.value = value

    def get_value(self) -> int:
        return self.value

def process_data(manager: DataManager):
    return manager.get_value()
"""
    metadata = parser.parse_content(code, "python", "sample.py")
    assert metadata.file_path == "sample.py"
    assert metadata.language == "python"
    assert len(metadata.imports) == 2
    assert "import os" in metadata.imports
    assert "from sys import path" in metadata.imports

    assert len(metadata.classes) == 1
    assert metadata.classes[0].name == "DataManager"
    assert metadata.classes[0].start_line == 5
    assert metadata.classes[0].end_line == 10

    assert len(metadata.functions) == 3
    func_names = [f.name for f in metadata.functions]
    assert "__init__" in func_names
    assert "get_value" in func_names
    assert "process_data" in func_names


def test_parse_js_ts_content():
    parser = ASTParser()
    code = b"""
import React from 'react';
import { Button } from '@mui/material';

class Toggle extends React.Component {
    render() {
        return <Button>Toggle</Button>;
    }
}

export const helper = () => {
    return true;
};
"""
    metadata = parser.parse_content(code, "tsx", "sample.tsx")
    assert metadata.file_path == "sample.tsx"
    assert metadata.language == "tsx"
    assert len(metadata.imports) == 2
    assert len(metadata.classes) == 1
    assert metadata.classes[0].name == "Toggle"
    assert len(metadata.functions) == 2
    func_names = [f.name for f in metadata.functions]
    assert "render" in func_names
    assert "helper" in func_names
