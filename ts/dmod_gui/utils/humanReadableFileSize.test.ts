import humanReadableFileSize from "./humanReadableFileSize";

describe("humanReadableFileSize", () => {
  it("0 bytes", () => {
    expect(humanReadableFileSize(0)).toBe("0 B");
  });

  it("1 bytes", () => {
    expect(humanReadableFileSize(1)).toBe("1 B");
  });

  it("1023 bytes", () => {
    expect(humanReadableFileSize(1023)).toBe("1023 B");
  });

  it("1 KB", () => {
    expect(humanReadableFileSize(1024)).toBe("1 kB");
  });

  it("1023 KB", () => {
    expect(humanReadableFileSize(Math.pow(1024, 2) - 1024)).toBe("1023 kB");
  });

  it("1 MB", () => {
    expect(humanReadableFileSize(Math.pow(1024, 2))).toBe("1 MB");
  });
  it("1023 MB", () => {
    expect(humanReadableFileSize(Math.pow(1024, 3) - Math.pow(1024, 2))).toBe(
      "1023 MB"
    );
  });
});
