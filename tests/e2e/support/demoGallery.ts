import { readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const demoGalleryRoot = join(tmpdir(), "selectiq-e2e-gallery");

export type DemoGallery = {
  valid: string[];
  corrupt: string;
  unsupported: string;
};

export function demoGallery(): DemoGallery {
  const valid = readdirSync(demoGalleryRoot)
    .filter((name) => name.endsWith(".jpg"))
    .sort()
    .map((name) => join(demoGalleryRoot, name));
  return {
    valid,
    corrupt: join(demoGalleryRoot, "invalid", "corrupt.jpg"),
    unsupported: join(demoGalleryRoot, "invalid", "notes.png"),
  };
}
