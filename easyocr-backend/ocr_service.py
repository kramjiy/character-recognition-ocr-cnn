import easyocr
import os
import numpy as np
from PIL import Image
import cv2

class OCRService:
    def __init__(self, languages=None):
        if languages is None:
            languages = ['en']
        self.reader = easyocr.Reader(
            languages,
            gpu=True,
            model_storage_directory="./easyocr_models",
            download_enabled=True,
            verbose=True
        )
        print(f"EasyOCR initialized with languages: {languages}")

    def _convert_to_serializable(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_to_serializable(value) for key, value in obj.items()}
        else:
            return obj

    def _advanced_preprocess(self, image_path):
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Sharpening
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharp = cv2.filter2D(gray, -1, kernel)

        # Adaptive threshold (Gaussian)
        thresh = cv2.adaptiveThreshold(
            sharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
        )

        # Morphological closing
        kernel_morph = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_morph)

        # Denoising
        denoised = cv2.fastNlMeansDenoising(morph, None, 10, 7, 21)

        # Resize (2x)
        h, w = denoised.shape
        resized = cv2.resize(denoised, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        path_out = image_path + "_adv_preprocessed.jpg"
        cv2.imwrite(path_out, resized)
        return path_out

    def extract_text(self, image_path, confidence_threshold=0.2):
        try:
            methods = {
                "original": image_path,
                "advanced": self._advanced_preprocess(image_path)
            }

            all_results = []
            for method_name, path in methods.items():
                results = self.reader.readtext(
                    path,
                    detail=1,
                    paragraph=False,
                    decoder="beamsearch",
                    beamWidth=10,
                    width_ths=0.7,
                    min_size=10,
                    link_threshold=0.5,
                    add_margin=0.1,
                    rotation_info=[90, 180, 270],
                    contrast_ths=0.1,
                )
                filtered = [
                    {
                        "text": text,
                        "confidence": float(prob),
                        "bounding_box": self._convert_to_serializable(bbox),
                        "method": method_name,
                    }
                    for (bbox, text, prob) in results
                    if float(prob) >= confidence_threshold
                ]
                all_results.extend(filtered)

            # Remove duplicates
            unique_results = self._remove_duplicates(all_results)

            # Sort results top-to-bottom, left-to-right
            sorted_results = self._sort_results_reading_order(unique_results)

            # Consolidate text respecting reading order
            consolidated_text = self._consolidate_text(sorted_results)

            # Clean temp files
            if os.path.exists(methods["advanced"]):
                try:
                    os.remove(methods["advanced"])
                except:
                    pass

            result = {
                "status": "success",
                "full_text": consolidated_text,
                "detailed_results": sorted_results,
            }
            return self._convert_to_serializable(result)

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _remove_duplicates(self, results, iou_threshold=0.5, text_similarity_threshold=0.7):
        if not results:
            return []

        def calculate_iou(box1, box2):
            b1 = [
                min(box1[0][0], box1[2][0]),
                min(box1[0][1], box1[2][1]),
                max(box1[0][0], box1[2][0]),
                max(box1[0][1], box1[2][1]),
            ]
            b2 = [
                min(box2[0][0], box2[2][0]),
                min(box2[0][1], box2[2][1]),
                max(box2[0][0], box2[2][0]),
                max(box2[0][1], box2[2][1]),
            ]
            x_left = max(b1[0], b2[0])
            y_top = max(b1[1], b2[1])
            x_right = min(b1[2], b2[2])
            y_bottom = min(b1[3], b2[3])
            if x_right < x_left or y_bottom < y_top:
                return 0.0
            intersection_area = (x_right - x_left) * (y_bottom - y_top)
            b1_area = (b1[2] - b1[0]) * (b1[3] - b1[1])
            b2_area = (b2[2] - b2[0]) * (b2[3] - b2[1])
            union_area = b1_area + b2_area - intersection_area
            return intersection_area / union_area if union_area > 0 else 0

        def text_similarity(t1, t2):
            t1, t2 = t1.lower(), t2.lower()
            if not t1 or not t2:
                return 0
            if t1 in t2 or t2 in t1:
                return 0.8
            common_chars = sum(1 for c in set(t1) if c in t2)
            total_chars = len(set(t1 + t2))
            return common_chars / total_chars if total_chars > 0 else 0

        sorted_results = sorted(results, key=lambda x: x["confidence"], reverse=True)
        unique = []
        for res in sorted_results:
            duplicate = False
            for u in unique:
                if (
                    calculate_iou(res["bounding_box"], u["bounding_box"]) > iou_threshold
                    and text_similarity(res["text"], u["text"]) > text_similarity_threshold
                ):
                    duplicate = True
                    break
            if not duplicate:
                unique.append(res)
        return unique

    def _sort_results_reading_order(self, results):
        """
        Sort text boxes top-to-bottom, then left-to-right within each line.
        """
        # Calculate average height of each box to help group lines
        def box_avg_y(box):
            return sum(point[1] for point in box) / len(box)

        # Sort by top coordinate first (y)
        results.sort(key=lambda r: box_avg_y(r["bounding_box"]))

        # Group results into lines based on vertical proximity
        lines = []
        line_thresh = 10  # pixels, tweak as needed

        for res in results:
            placed = False
            y_center = box_avg_y(res["bounding_box"])
            for line in lines:
                # Check vertical distance to line
                line_ys = [box_avg_y(r["bounding_box"]) for r in line]
                if min(abs(y_center - y) for y in line_ys) < line_thresh:
                    line.append(res)
                    placed = True
                    break
            if not placed:
                lines.append([res])

        # Sort each line's results left to right
        def box_avg_x(box):
            return sum(point[0] for point in box) / len(box)

        sorted_results = []
        for line in lines:
            line.sort(key=lambda r: box_avg_x(r["bounding_box"]))
            sorted_results.extend(line)

        return sorted_results

    def _consolidate_text(self, results):
        if not results:
            return ""
        text = " ".join(r["text"] for r in results)
        return " ".join(text.split())
