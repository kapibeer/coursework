from collections import defaultdict

from chonkie import SentenceChunker


class RecursiveChunker:
    def chunk(self, elements: list, chunk_size: int = 512, overlap: int = 64) -> list[str]:
        if not elements:
            return []

        sentence_chunker = SentenceChunker(chunk_size=chunk_size, chunk_overlap=overlap)
        blocks: dict[tuple[int, int], list] = defaultdict(list)

        for element in elements:
            blocks[(element.page, element.cluster)].append(element)

        chunks: list[str] = []
        for key in sorted(blocks):
            ordered = sorted(blocks[key], key=lambda item: (item.y0, item.x0))
            block_text = "\n".join(element.text.strip() for element in ordered if element.text.strip())
            if not block_text:
                continue

            for chunk in sentence_chunker.chunk(block_text):
                chunk_text = getattr(chunk, "text", str(chunk)).strip()
                if chunk_text:
                    chunks.append(chunk_text)

        return chunks
