import pytest
from unittest.mock import Mock, patch
from src.core.preprocessor.preprocessor import Preprocessor
from src.core.models.preprocessor import LayoutType, PageOrientation, RejectionReason

class MockPdfProvider:
    def __init__(self):
        self.encrypted = False
        self.pages = 10
        self.metadata = {"title": "Test"}
        self.layout_type = LayoutType.SINGLE_COLUMN
        self.page_orientation = PageOrientation.PORTRAIT
        self.mixed_layout = False
        self.text_layer = True
        self.scanned = False
        self.elements = {}
        self.open_called = False
        self.close_called = False
        self.should_fail_open = False

    def open(self, path):
        self.open_called = True
        if self.should_fail_open:
            raise Exception("Corrupt")
    def close(self):
        self.close_called = True
    def is_encrypted(self): return self.encrypted
    def get_page_count(self): return self.pages
    def get_metadata(self): return self.metadata
    def analyze_layout_and_orientation(self): return self.layout_type, self.page_orientation, self.mixed_layout
    def has_text_layer(self): return self.text_layer
    def is_likely_scanned(self): return self.scanned
    def detect_elements(self): return self.elements

@pytest.fixture
def mock_provider():
    return MockPdfProvider()

@pytest.fixture
def preprocessor(mock_provider):
    return Preprocessor(mock_provider)

@patch('src.shared.utils.file_utils.file_exists')
@patch('src.shared.utils.file_utils.get_file_extension')
@patch('src.shared.utils.file_utils.get_file_size_mb')
def test_preprocessor_accepts_valid_pdf(mock_size, mock_ext, mock_exists, preprocessor, mock_provider):
    mock_exists.return_value = True
    mock_ext.return_value = "pdf"
    mock_size.return_value = 5.0
    
    result = preprocessor.process("test.pdf")
    
    assert result.status == "accepted"
    assert result.document_profile is not None
    assert result.document_profile.pages == 10
    assert result.document_profile.size_mb == 5.0
    assert result.document_profile.layout_type == LayoutType.SINGLE_COLUMN
    assert mock_provider.open_called
    assert mock_provider.close_called

@patch('src.shared.utils.file_utils.file_exists')
def test_preprocessor_rejects_missing_file(mock_exists, preprocessor):
    mock_exists.return_value = False
    result = preprocessor.process("missing.pdf")
    assert result.status == "rejected"
    assert result.reason == RejectionReason.FILE_NOT_FOUND

@patch('src.shared.utils.file_utils.file_exists')
@patch('src.shared.utils.file_utils.get_file_extension')
def test_preprocessor_rejects_unsupported_ext(mock_ext, mock_exists, preprocessor):
    mock_exists.return_value = True
    mock_ext.return_value = "docx"
    result = preprocessor.process("test.docx")
    assert result.status == "rejected"
    assert result.reason == RejectionReason.FILE_UNSUPPORTED

@patch('src.shared.utils.file_utils.file_exists')
@patch('src.shared.utils.file_utils.get_file_extension')
@patch('src.shared.utils.file_utils.get_file_size_mb')
def test_preprocessor_rejects_oversized_file(mock_size, mock_ext, mock_exists, preprocessor):
    mock_exists.return_value = True
    mock_ext.return_value = "pdf"
    mock_size.return_value = 15.0
    result = preprocessor.process("large.pdf")
    assert result.status == "rejected"
    assert result.reason == RejectionReason.FILE_TOO_LARGE

@patch('src.shared.utils.file_utils.file_exists')
@patch('src.shared.utils.file_utils.get_file_extension')
@patch('src.shared.utils.file_utils.get_file_size_mb')
def test_preprocessor_rejects_encrypted(mock_size, mock_ext, mock_exists, preprocessor, mock_provider):
    mock_exists.return_value = True
    mock_ext.return_value = "pdf"
    mock_size.return_value = 5.0
    mock_provider.encrypted = True
    
    result = preprocessor.process("encrypted.pdf")
    assert result.status == "rejected"
    assert result.reason == RejectionReason.PASSWORD_PROTECTED

@patch('src.shared.utils.file_utils.file_exists')
@patch('src.shared.utils.file_utils.get_file_extension')
@patch('src.shared.utils.file_utils.get_file_size_mb')
def test_preprocessor_adds_warnings(mock_size, mock_ext, mock_exists, preprocessor, mock_provider):
    mock_exists.return_value = True
    mock_ext.return_value = "pdf"
    mock_size.return_value = 5.0
    
    mock_provider.pages = 400
    mock_provider.scanned = True
    
    result = preprocessor.process("test.pdf")
    assert result.status == "accepted"
    assert len(result.document_profile.warnings) == 2
    assert "Document exceeds 300 pages." in result.document_profile.warnings
    assert "Document appears to be scanned." in result.document_profile.warnings
