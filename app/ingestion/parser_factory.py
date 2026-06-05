from app.ingestion.base_parser import FileParser
from app.ingestion.csv_parser import CSVParser
from app.core.exceptions import InvalidFileTypeException


class ParserFactory:
    """
    Factory Pattern: Selects the correct FileParser based on file MIME type.
    
    To add a new format:
      1. Create ExcelParser(FileParser) in excel_parser.py
      2. Register it here in _parsers list.
      Done. Zero other changes.
    """

    _parsers: list[FileParser] = [
        CSVParser(),
    ]

    @classmethod
    def get_parser(cls, mime_type: str) -> FileParser:
        for parser in cls._parsers:
            if mime_type in parser.supported_mime_types:
                return parser
        raise InvalidFileTypeException(mime_type)