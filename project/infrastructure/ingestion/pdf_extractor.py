from dataclasses import dataclass
import re

from pypdf import PdfReader


@dataclass(slots=True)
class LayoutElement:
    text: str
    x0: float
    x1: float
    y0: float
    y1: float
    page: int
    type: str
    cluster: int = 0


class PdfTextExtractor:
    _UNI_PATTERN = re.compile(r"/uni([0-9A-Fa-f]{4,6})")
    _BROKEN_UNI_PATTERN = re.compile(r"/uni[0-9A-Fa-f]{4,6}")

    def extract(self, pdf_path: str) -> list[LayoutElement]:
        reader = PdfReader(pdf_path)
        elements: list[LayoutElement] = []
        seen_texts: set[str] = set()

        for page_index, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                continue

            blocks = [block.strip() for block in page_text.split("\n\n") if block.strip()]
            for block_index, block in enumerate(blocks, start=1):
                decoded_block = self._decode_unicode_escapes(block)
                normalized = " ".join(line.strip() for line in decoded_block.splitlines() if line.strip()).strip()
                if self._has_broken_unicode_escapes(normalized):
                    raise ValueError(
                        "PDF extraction produced undecoded unicode escapes. "
                        "Источник не будет проиндексирован, пока текст не читается корректно."
                    )
                if not normalized or normalized.isdigit() or normalized in seen_texts:
                    continue

                seen_texts.add(normalized)
                y_top = float(block_index * 20)
                elements.append(
                    LayoutElement(
                        text=normalized,
                        x0=0.0,
                        x1=100.0,
                        y0=y_top,
                        y1=y_top + 10.0,
                        page=page_index,
                        type="Text",
                    )
                )

        return elements

    @classmethod
    def _decode_unicode_escapes(cls, text: str) -> str:
        if "/uni" not in text:
            return text

        decoded = cls._UNI_PATTERN.sub(lambda match: chr(int(match.group(1), 16)), text)
        decoded = decoded.replace("\u00A0", " ")
        return decoded

    @classmethod
    def _has_broken_unicode_escapes(cls, text: str) -> bool:
        return len(cls._BROKEN_UNI_PATTERN.findall(text)) >= 3
