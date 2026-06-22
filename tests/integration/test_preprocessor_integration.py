import pytest
import os
from src.core.preprocessor.preprocessor import Preprocessor
from src.adapters.pdf.pymupdf_provider import PyMuPdfProvider
from src.core.models.preprocessor import RejectionReason

@pytest.fixture(scope="module")
def setup_dummy_pdf(tmp_path_factory):
    import fitz
    test_dir = tmp_path_factory.mktemp("pdf_data")
    
    valid_path = test_dir / "valid.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World!")
    doc.save(str(valid_path))
    doc.close()
    
    encrypted_path = test_dir / "encrypted.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Secret")
    doc.save(str(encrypted_path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="123")
    doc.close()

    return {
        "valid": str(valid_path),
        "encrypted": str(encrypted_path),
        "missing": str(test_dir / "missing.pdf"),
        "invalid_ext": str(test_dir / "test.txt")
    }

def test_integration_valid_pdf(setup_dummy_pdf):
    provider = PyMuPdfProvider()
    preprocessor = Preprocessor(provider)
    
    result = preprocessor.process(setup_dummy_pdf["valid"])
    assert result.status == "accepted"
    assert result.document_profile.pages == 1
    assert result.document_profile.text_layer_present is True
    assert result.document_profile.likely_scanned is False

def test_integration_encrypted_pdf(setup_dummy_pdf):
    provider = PyMuPdfProvider()
    preprocessor = Preprocessor(provider)
    
    result = preprocessor.process(setup_dummy_pdf["encrypted"])
    assert result.status == "rejected"
    assert result.reason == RejectionReason.PASSWORD_PROTECTED

def test_integration_missing_file(setup_dummy_pdf):
    provider = PyMuPdfProvider()
    preprocessor = Preprocessor(provider)
    
    result = preprocessor.process(setup_dummy_pdf["missing"])
    assert result.status == "rejected"
    assert result.reason == RejectionReason.FILE_NOT_FOUND
