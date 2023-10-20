export const humanReadableFileSize = (size: number): string => {
  const sizes = ["B", "kB", "MB", "GB", "TB"];

  const order = size <= 0 ? 0 : Math.floor(Math.log(size) / Math.log(1024));
  const scaled_size = size / Math.pow(1024, order);

  // B, kB, and MB have no digits after decimal place
  if (order < 3) {
    return `${scaled_size.toFixed(0)} ${sizes[order]}`;
  }
  return `${scaled_size.toFixed(1)} ${sizes[order]}`;
};

export default humanReadableFileSize;
