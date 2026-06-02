from collections import defaultdict

import numpy as np
from scipy.ndimage import binary_dilation, label


class LayoutSegmenter:
    def segment(
        self,
        elements: list,
        x_bins: int = 100,
        y_bins: int = 100,
        threshold: float = 0.05,
    ) -> list:
        if not elements:
            return []

        segmented: list = []
        next_cluster = 1

        pages: dict[int, list] = defaultdict(list)
        for element in elements:
            pages[element.page].append(element)

        for _, page_elements in sorted(pages.items()):
            page_width = max((element.x1 for element in page_elements), default=1.0)
            page_height = max((element.y1 for element in page_elements), default=1.0)
            if page_width <= 0 or page_height <= 0:
                for element in sorted(page_elements, key=lambda item: (item.y0, item.x0)):
                    element.cluster = next_cluster
                    segmented.append(element)
                    next_cluster += 1
                continue

            heatmap = np.zeros((y_bins, x_bins), dtype=np.float32)
            for element in page_elements:
                x0 = int(np.clip((element.x0 / page_width) * (x_bins - 1), 0, x_bins - 1))
                x1 = int(np.clip((element.x1 / page_width) * (x_bins - 1), 0, x_bins - 1))
                y0 = int(np.clip((element.y0 / page_height) * (y_bins - 1), 0, y_bins - 1))
                y1 = int(np.clip((element.y1 / page_height) * (y_bins - 1), 0, y_bins - 1))
                heatmap[min(y0, y1) : max(y0, y1) + 1, min(x0, x1) : max(x0, x1) + 1] += 1

            mask = heatmap >= max(heatmap.max() * threshold, 1.0)
            mask = binary_dilation(mask, iterations=2)
            labeled, _ = label(mask)

            groups: dict[int, list] = defaultdict(list)
            leftovers: list = []

            for element in page_elements:
                center_x = (element.x0 + element.x1) / 2
                center_y = (element.y0 + element.y1) / 2
                x_idx = int(np.clip((center_x / page_width) * (x_bins - 1), 0, x_bins - 1))
                y_idx = int(np.clip((center_y / page_height) * (y_bins - 1), 0, y_bins - 1))
                component = int(labeled[y_idx, x_idx])
                if component <= 0:
                    leftovers.append(element)
                    continue
                groups[component].append(element)

            ordered_groups = []
            for _, group in sorted(
                groups.items(),
                key=lambda item: min((element.y0 for element in item[1]), default=0.0),
            ):
                columns = self._split_columns(group, page_width)
                ordered_groups.extend(columns)

            for group in ordered_groups:
                for element in sorted(group, key=lambda item: (item.y0, item.x0)):
                    element.cluster = next_cluster
                    segmented.append(element)
                next_cluster += 1

            if leftovers:
                for element in sorted(leftovers, key=lambda item: (item.y0, item.x0)):
                    element.cluster = next_cluster
                    segmented.append(element)
                    next_cluster += 1

        return segmented

    def _split_columns(self, elements: list, page_width: float) -> list[list]:
        if len(elements) <= 1:
            return [elements]

        sorted_elements = sorted(elements, key=lambda item: (item.x0 + item.x1) / 2)
        column_gap = max(page_width * 0.12, 40.0)

        columns: list[list] = [[sorted_elements[0]]]
        previous_center = (sorted_elements[0].x0 + sorted_elements[0].x1) / 2

        for element in sorted_elements[1:]:
            center = (element.x0 + element.x1) / 2
            if center - previous_center > column_gap:
                columns.append([element])
            else:
                columns[-1].append(element)
            previous_center = center

        return sorted(
            columns,
            key=lambda column: min((element.x0 for element in column), default=0.0),
        )
