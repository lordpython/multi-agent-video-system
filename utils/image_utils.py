#!/usr/bin/env python3
"""
Utility functions for handling image data safely.
"""

from typing import Dict, Any, List
from pathlib import Path


def sanitize_image_result_for_logging(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize image generation result for safe logging by removing binary data.

    Args:
        result: Raw image generation result containing binary data

    Returns:
        Sanitized result safe for logging/printing
    """
    sanitized = {
        "prompt": result.get("prompt"),
        "total_images": result.get("total_images", 0),
        "source": result.get("source"),
        "model": result.get("model"),
        "images_info": [],
    }

    if "images" in result:
        for img in result["images"]:
            img_info = {
                "status": img.get("status"),
                "width": img.get("width"),
                "height": img.get("height"),
                "size_bytes": len(img.get("image_bytes", b"")),
                "mime_type": img.get("mime_type"),
                "image_id": img.get("image_id"),
                "error": img.get("error") if img.get("status") == "error" else None,
            }
            sanitized["images_info"].append(img_info)

    return sanitized


def save_images_to_files(
    result: Dict[str, Any], output_dir: str = "generated_images"
) -> List[str]:
    """
    Save generated images to files.

    Args:
        result: Image generation result containing image data
        output_dir: Directory to save images to

    Returns:
        List of file paths where images were saved
    """
    saved_files = []

    if result.get("total_images", 0) == 0:
        return saved_files

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    if "images" in result:
        for i, img in enumerate(result["images"]):
            if img.get("status") == "success" and "image_bytes" in img:
                # Determine file extension
                ext = "jpg" if img.get("mime_type") == "image/jpeg" else "png"
                filename = f"image_{i + 1}.{ext}"
                file_path = output_path / filename

                # Save the image
                with open(file_path, "wb") as f:
                    f.write(img["image_bytes"])

                saved_files.append(str(file_path))

    return saved_files


def print_image_generation_summary(
    result: Dict[str, Any], save_files: bool = True
) -> None:
    """
    Print a clean summary of image generation results.

    Args:
        result: Image generation result
        save_files: Whether to save images to files
    """
    # Print sanitized result
    sanitized = sanitize_image_result_for_logging(result)
    print(f"Result: {sanitized}")

    if result.get("total_images", 0) > 0:
        print("✅ Image generation successful")
        print(f"📊 Generated {result['total_images']} image(s)")

        if save_files:
            saved_files = save_images_to_files(result)
            for file_path in saved_files:
                print(f"📁 Image saved to: {file_path}")

                # Get file size
                file_size = Path(file_path).stat().st_size
                print(f"   Size: {file_size} bytes")

                # Get dimensions from result
                img_index = int(Path(file_path).stem.split("_")[-1]) - 1
                if img_index < len(result.get("images", [])):
                    img = result["images"][img_index]
                    print(f"   Dimensions: {img.get('width')}x{img.get('height')}")
    else:
        print("⚠️ Image generation completed but no images returned")
