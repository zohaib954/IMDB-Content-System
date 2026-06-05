from abc import ABC, abstractmethod
from typing import Generator


class FileParser(ABC):
    """
    Abstract base class for all file parsers.
    
    SOLID - Open/Closed Principle:
    To support a new file format (Excel, JSON, XML), create a new class
    that inherits from FileParser and implements parse().
    No existing code needs to change.
    """

    CHUNK_SIZE = 1000  # rows per chunk for memory-efficient processing

    @abstractmethod
    def validate(self, file) -> None:
        """
        Validate the file before parsing.
        Raises AppException subclasses on failure.
        """
        pass

    @abstractmethod
    def parse(self, file) -> Generator[list[dict], None, None]:
        """
        Parse file and yield chunks of records.
        Must be a generator to support files up to 1GB without
        loading everything into memory.
        
        Yields:
            list[dict]: A chunk of CHUNK_SIZE parsed records.
        """
        pass

    @property
    @abstractmethod
    def supported_mime_types(self) -> list[str]:
        """Return list of MIME types this parser handles."""
        pass