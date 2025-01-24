from dataclasses import dataclass
from flask import Flask, jsonify, send_file, request, abort, make_response
import logging
import os
from pathlib import Path
import json
import re
import subprocess
import tempfile
from typing import Tuple, Optional

AspectRatio = Tuple[int, int]
app = Flask(__name__, static_url_path="")

# Configure image collection path
COLLECTION_PATH = Path(os.path.expanduser("~/.jpegtranweb/collection"))
COLLECTION_PATH.mkdir(parents=True, exist_ok=True)

# Example image path
EXAMPLE_IMAGE_PATH = Path(__file__).parent / "example.jpg"


@dataclass
class CropBox:
    left: int
    right: int
    top: int
    bottom: int

    def validate_for_aspect_ratio(self, aspect_ratio: AspectRatio) -> bool:
        """Check if aspect ratio matches (with small tolerance)"""
        fraction = (self.right - self.left) / (self.bottom - self.top)
        expected_fraction = aspect_ratio[0] / aspect_ratio[1]
        return abs(fraction - expected_fraction) < 0.01
    
    def validate_for_image(self, img_size: AspectRatio) -> bool:
        """Validate if crop box is maximized in one dimension."""
        img_width, img_height = img_size
        box_width = self.right - self.left
        box_height = self.bottom - self.top
        
        box_ratio = box_width / box_height
        
        # Check if box is within image bounds
        if (self.left < 0 or self.top < 0 or 
            self.right > img_width or self.bottom > img_height):
            return False

        # Check if maximized in one dimension
        if abs(box_width - img_width) < 1 or abs(box_height - img_height) < 1:
            return True
            
        return False


def get_image_files() -> list[str]:
    """Get sorted list of JPEG files in collection."""
    return sorted([f.name for f in COLLECTION_PATH.glob("*.jp*g")])

def get_image_info(i: int) -> dict:
    """Get information about image at index i including prev/next."""
    files = get_image_files()
    if not files:
        return {
            "current": None,
            "prev": None,
            "next": None,
            "total": 0
        }
    
    i = max(0, min(i, len(files) - 1))
    return {
        "current": files[i],
        "prev": files[i - 1] if i > 0 else None,
        "next": files[i + 1] if i < len(files) - 1 else None,
        "total": len(files)
    }


def raw_abort(status_code: int, description: Optional[str] = None) -> None:
    """Abort with custom description."""
    response = make_response(description)
    response.status_code = status_code
    abort(response)


@app.route("/iter/<int:i>")
def get_iteration(i: int):
    """Get info about image at index i."""
    return jsonify(get_image_info(i))

@app.route("/image/<filename>")
def get_image(filename: str):
    """Serve an image file."""
    if filename == "example":
        if not EXAMPLE_IMAGE_PATH.is_file():
            raw_abort(404, description="Example image not found")
        return send_file(EXAMPLE_IMAGE_PATH)
        
    file_path = COLLECTION_PATH / filename
    if not file_path.is_file():
        abort(404)
    return send_file(file_path)


@dataclass
class TranRequest:
    box: CropBox
    aspectRatio: AspectRatio


@app.route("/tran/<filename>", methods=["POST"])
def transform_image(filename: str):
    """Crop image using jpegtran."""
    if filename == "example":
        raw_abort(400, description="Cannot crop the example image")
        
    file_path = COLLECTION_PATH / filename
    if not file_path.is_file():
        raw_abort(404, description="Image not found")
        
    data = request.json
    if not data:
        raw_abort(400, description="Request data is not a valid JSON")

    try:
        data = dict(data, box=CropBox(**data["box"]))
        tran_request = TranRequest(**data)
    except TypeError:
        logging.error(data)
        raw_abort(400, description="Invalid request data")

    if not tran_request.box.validate_for_aspect_ratio(tran_request.aspectRatio):
        logging.error(tran_request)
        raw_abort(400, description="Invalid aspect ratio")

    # Get image dimensions using rdjpgcom
    try:
        result = subprocess.run(
            ["rdjpgcom", "-verbose", str(file_path)],
            capture_output=True,
            text=True
        )
        # It prints like this:
        # JPEG image is 640w * 360h, 3 color components, 8 bits per sample
        # JPEG process: Baseline
        matches = re.search(r"JPEG image is (\d+)w \* (\d+)h", result.stdout)
        image_aspect_ratio = int(matches.group(1)), int(matches.group(2))
    except Exception as e:
        logging.error(f"Failed to get image info: {str(e)}")
        logging.error(result.stderr)
        logging.error(result.stdout)
        raw_abort(500, description=f"Failed to get image info: {str(e)}")
    if not tran_request.box.validate_for_image(image_aspect_ratio):
        logging.error(image_aspect_ratio)
        raw_abort(400, description="Invalid crop box dimensions")

    try:
        run_jpegtran(file_path, tran_request.box)
    except subprocess.CalledProcessError as e:
        logging.error(f"jpegtran failed: {str(e)}")
        raw_abort(500, description=f"jpegtran failed: {str(e)}")
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        raw_abort(500, description=f"Error processing image: {str(e)}")
    return jsonify({"status": "success"})


def run_jpegtran(file_path: Path, crop_box: CropBox) -> subprocess.CompletedProcess:
    """Run jpegtran to crop image."""
    # Create crop command argument
    crop_spec = (
        f"{crop_box.right-crop_box.left}x"
        f"{crop_box.bottom-crop_box.top}+"
        f"{crop_box.left}+{crop_box.top}"
    )
    # Create temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir=file_path.parent) as temp_file:
        # Need to use the same directory as the original file so that
        # `Path.replace` works.
        temp_path = Path(temp_file.name)
        jpegtran_process = subprocess.run(
            [
                # Although `-copy all` seems to persist image dimensions
                # which doesn’t make much sense and would cause issues
                # with subsequent transformations (rdjpgcom used above),
                # it’s needed to preserve EXIF data.
                "jpegtran", "-crop", crop_spec, "-copy", "all", "-outfile", 
                str(temp_path), str(file_path)],
            check=True
        )
        
        # Preserve original file timestamps
        try:
            original_stat = os.stat(file_path)
            os.utime(temp_path, (original_stat.st_atime, original_stat.st_mtime))
        except Exception as e:
            logging.warning(f"Failed to touch the file: {str(e)}")

        # Replace original with cropped version
        temp_path.replace(file_path)
    return jpegtran_process
