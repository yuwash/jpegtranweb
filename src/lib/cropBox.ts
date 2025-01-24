export interface CropBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface ImageDimensions {
  width: number;
  height: number;
}

export function calculateCropBox(
  imageDimensions: ImageDimensions,
  aspectRatio: number
): CropBox {
  const { width: imgWidth, height: imgHeight } = imageDimensions;
  const imageRatio = imgWidth / imgHeight;

  let boxWidth: number;
  let boxHeight: number;

  if (aspectRatio > imageRatio) {
    // Desired ratio is wider than image ratio - maximize height
    boxHeight = imgHeight;
    boxWidth = imgHeight * aspectRatio;
  } else {
    // Desired ratio is taller than image ratio - maximize width
    boxWidth = imgWidth;
    boxHeight = imgWidth / aspectRatio;
  }

  // If calculated dimensions exceed image bounds, scale down
  if (boxWidth > imgWidth) {
    const scale = imgWidth / boxWidth;
    boxWidth *= scale;
    boxHeight *= scale;
  }
  if (boxHeight > imgHeight) {
    const scale = imgHeight / boxHeight;
    boxWidth *= scale;
    boxHeight *= scale;
  }

  // Center the box
  const left = (imgWidth - boxWidth) / 2;
  const top = (imgHeight - boxHeight) / 2;

  return {
    left,
    top,
    right: left + boxWidth,
    bottom: top + boxHeight
  };
}