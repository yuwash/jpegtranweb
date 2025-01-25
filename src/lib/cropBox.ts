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

  if (aspectRatio < imageRatio) {
    // Desired ratio is wider than image ratio - maximize height
    boxHeight = imgHeight;
    boxWidth = Math.min(Math.floor(imgHeight * aspectRatio), imgWidth);
    // Use of imgWidth may be necessary when aspectRatio is close to imageRatio
  } else {
    // Desired ratio is taller than image ratio - maximize width
    boxWidth = imgWidth;
    boxHeight = Math.min(Math.floor(imgWidth / aspectRatio), imgHeight);
    // Use of imgHeight may be necessary when aspectRatio is close to imageRatio
  }

  // Center the box
  const left = Math.floor((imgWidth - boxWidth) / 2);
  const top = Math.floor((imgHeight - boxHeight) / 2);

  return {
    left,
    top,
    right: left + boxWidth,
    bottom: top + boxHeight
  };
}