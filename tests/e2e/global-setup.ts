import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";

import { demoGalleryRoot } from "./support/demoGallery";

export default function globalSetup() {
  const venvPython = "backend/.venv/bin/python";
  const python = existsSync(venvPython) ? venvPython : "python3";
  execFileSync(python, ["scripts/make_demo_gallery.py", "--out", demoGalleryRoot], {
    stdio: "inherit",
  });
}
