"""
Pluggable Multilingual Language Registry for Indian Medical Documents.
"""

import subprocess
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LanguageInfo(BaseModel):
    """Metadata describing a supported or pluggable language."""
    model_config = ConfigDict(frozen=True)

    code: str = Field(description="ISO 639-1 / 639-2 language code (e.g. 'en', 'hi', 'mr')")
    display_name: str
    native_name: str
    script: str = Field(description="Primary writing script ('Latin', 'Devanagari', etc.)")
    ocr_pack: str = Field(description="Tesseract language code (e.g. 'eng', 'hin', 'mar')")
    ocr_available: bool = False
    extraction_supported: bool = True
    generation_supported: bool = True
    validation_status: str = "VALIDATED"
    limitations: List[str] = Field(default_factory=list)


class LanguageRegistry:
    """Central registry and diagnostic service for supported Indian languages."""

    def __init__(self):
        self._installed_ocr_packs = self._detect_installed_tesseract_languages()
        self._languages: Dict[str, LanguageInfo] = {
            "en": LanguageInfo(
                code="en",
                display_name="English",
                native_name="English",
                script="Latin",
                ocr_pack="eng",
                ocr_available="eng" in self._installed_ocr_packs,
                extraction_supported=True,
                generation_supported=True,
                validation_status="PRODUCTION_VERIFIED",
                limitations=[],
            ),
            "hi": LanguageInfo(
                code="hi",
                display_name="Hindi",
                native_name="हिन्दी",
                script="Devanagari",
                ocr_pack="hin",
                ocr_available="hin" in self._installed_ocr_packs,
                extraction_supported=True,
                generation_supported=True,
                validation_status="VALIDATED",
                limitations=["Mixed-script clinical notes require Devanagari Unicode NFKC normalization."],
            ),
            "mr": LanguageInfo(
                code="mr",
                display_name="Marathi",
                native_name="मराठी",
                script="Devanagari",
                ocr_pack="mar",
                ocr_available="mar" in self._installed_ocr_packs,
                extraction_supported=True,
                generation_supported=True,
                validation_status="VALIDATED",
                limitations=["Shares Devanagari script with Hindi; disambiguation relies on lexical and letter 'ळ' markers."],
            ),
            # Pluggable regional languages documented with explicit availability status
            "gu": LanguageInfo(
                code="gu",
                display_name="Gujarati",
                native_name="ગુજરાતી",
                script="Gujarati",
                ocr_pack="guj",
                ocr_available="guj" in self._installed_ocr_packs,
                extraction_supported=False,
                generation_supported=False,
                validation_status="PLANNED",
                limitations=["OCR language pack and clinical evaluation benchmark pending."],
            ),
            "bn": LanguageInfo(
                code="bn",
                display_name="Bengali",
                native_name="বাংলা",
                script="Bengali",
                ocr_pack="ben",
                ocr_available="ben" in self._installed_ocr_packs,
                extraction_supported=False,
                generation_supported=False,
                validation_status="PLANNED",
                limitations=["OCR language pack and clinical evaluation benchmark pending."],
            ),
            "ta": LanguageInfo(
                code="ta",
                display_name="Tamil",
                native_name="தமிழ்",
                script="Tamil",
                ocr_pack="tam",
                ocr_available="tam" in self._installed_ocr_packs,
                extraction_supported=False,
                generation_supported=False,
                validation_status="PLANNED",
                limitations=["Dravidian script adapter and clinical vocabulary pending."],
            ),
        }

    @staticmethod
    def _detect_installed_tesseract_languages() -> List[str]:
        """Detect which Tesseract language packs are physically installed on the host system."""
        try:
            res = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0:
                lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
                # Ignore header line ("List of installed languages...")
                return [lang for lang in lines if not lang.lower().startswith("list of")]
        except Exception:
            pass
        return ["eng"]

    def get_language(self, code: str) -> Optional[LanguageInfo]:
        return self._languages.get(code.lower().strip())

    def get(self, code: str) -> Optional[LanguageInfo]:
        return self.get_language(code)

    def is_supported(self, code: str) -> bool:
        lang = self.get_language(code)
        return lang is not None and lang.generation_supported

    def list_supported_languages(self) -> List[LanguageInfo]:
        """Returns all fully implemented and supported languages (English, Hindi, Marathi)."""
        return [lang for lang in self._languages.values() if lang.generation_supported]

    def get_supported_languages(self) -> List[str]:
        return [lang.code for lang in self.list_supported_languages()]

    def list_all_registered(self) -> List[LanguageInfo]:
        """Returns all registered languages including planned pluggable languages."""
        return list(self._languages.values())

    def list_all(self) -> List[LanguageInfo]:
        return self.list_all_registered()

    def get_installed_ocr_packs(self) -> List[str]:
        return list(self._installed_ocr_packs)


language_registry = LanguageRegistry()
