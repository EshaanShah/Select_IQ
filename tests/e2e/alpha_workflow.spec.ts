import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { demoGallery } from "./support/demoGallery";

const brief = "Peak action and candid celebration; skip empty frames.";
const realAi = process.env.SELECTIQ_E2E_REAL_AI === "1";
const analysisTimeout = realAi ? 300_000 : 30_000;

type DemoResult = {
  beforeChoices: string[];
  proposed: string[];
  removed: string;
  csvRows: string[][];
};

function proposalGrid(page: Page) {
  return page.getByRole("list", { name: "Proposed photographs" });
}

function selectionCount(page: Page, text: string) {
  return page.getByRole("region", { name: "Generate a proposal" }).getByText(text);
}

function steps(page: Page) {
  return page.getByRole("list", { name: "Demo steps" });
}

async function uploadGallery(page: Page, files: string[]) {
  await page.goto("/");
  await page.getByLabel("Choose files").setInputFiles(files);
  await page.getByRole("button", { name: "Import selected photographs" }).click();
}

async function saveBrief(page: Page, target: number) {
  await page.getByLabel("Creative brief").fill(brief);
  await page.getByLabel("Target number of photographs").fill(String(target));
  await page.getByRole("button", { name: "Save brief and target" }).click();
  await expect(page.getByText("Brief and target saved.")).toBeVisible();
}

async function analyze(page: Page) {
  await page.getByRole("button", { name: "Analyze gallery" }).click();
  await expect(page.getByText(/^Interpreted by /)).toBeVisible({ timeout: analysisTimeout });
  await expect(steps(page).locator("[aria-current=step]")).toContainText("Make 5 A/B choices");
}

async function generate(page: Page, version: number) {
  await page.getByRole("button", { name: "Generate proposal" }).click();
  await expect(page.getByText(`Proposal version ${version}`)).toBeVisible();
  return proposalGrid(page).locator(".filename").allTextContents();
}

async function makeChoices(page: Page) {
  await page.getByRole("button", { name: "Start comparisons" }).click();
  for (let choice = 1; choice <= 5; choice += 1) {
    await expect(page.getByText(`Comparison ${choice} of 5`)).toBeVisible();
    await page.getByRole("button", { name: /^Prefer / }).last().click();
  }
  await expect(page.getByText("Comparison session complete")).toBeVisible();
  await expect(steps(page)).toContainText("Done: 5 of 5 choices");
}

async function runDemo(page: Page): Promise<DemoResult> {
  const gallery = demoGallery();
  await uploadGallery(page, gallery.valid);
  await expect(page.getByLabel(`${gallery.valid.length} photos accepted`)).toBeVisible();
  await saveBrief(page, 5);
  await analyze(page);

  const beforeChoices = await generate(page, 1);
  await makeChoices(page);
  const proposed = await generate(page, 2);
  await expect(selectionCount(page, "5 of 5 selected")).toBeVisible();
  await expect(page.getByRole("note")).toContainText("Based on 5 saved choices");

  const removed = proposed[1];
  await proposalGrid(page).getByRole("button", { name: `Remove ${removed}` }).click();
  await expect(selectionCount(page, "4 of 5 selected")).toBeVisible();
  await expect(steps(page).locator("[aria-current=step]")).toContainText("4 of 5 selected");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Export CSV (4 photos)" }).click(),
  ]);
  const csv = readFileSync((await download.path())!, "utf8");
  const csvRows = csv.trim().split("\n").map((line) => line.split(","));
  return { beforeChoices, proposed, removed, csvRows };
}

test.describe("SelectIQ Alpha guided demo", () => {
  test.skip(realAi, "Offline scenarios run without SELECTIQ_E2E_REAL_AI.");

  test("upload → brief/target → analysis → 5 A/B choices → proposal → remove → export", async ({
    page,
  }) => {
    const gallery = demoGallery();
    const result = await runDemo(page);

    await expect(page.getByRole("note")).toContainText("Test signals, not AI");
    await expect(page.getByRole("note")).not.toContainText("AI-informed proposal");
    expect(result.proposed).not.toEqual(result.beforeChoices);
    await expect(proposalGrid(page).getByRole("listitem")).toHaveCount(5);
    await expect(
      proposalGrid(page).getByRole("listitem", { name: `${result.removed}, removed` }),
    ).toBeVisible();

    const [header, ...rows] = result.csvRows;
    expect(header).toEqual(["photo_id", "original_filename"]);
    expect(rows.map((row) => row[1])).toEqual(result.proposed.filter((name) => name !== result.removed));
    expect(new Set(rows.map((row) => row[0])).size).toBe(4);
    const uploaded = gallery.valid.map((file) => file.split("/").pop());
    for (const [, filename] of rows) expect(uploaded).toContain(filename);
  });

  test("failure paths explain what went wrong and how to recover", async ({ page }) => {
    const gallery = demoGallery();
    await uploadGallery(page, [...gallery.valid.slice(0, 10), gallery.corrupt, gallery.unsupported]);
    await expect(page.getByLabel("10 photos accepted")).toBeVisible();
    const attention = page.getByRole("region", { name: "Files that need attention" });
    await expect(attention).toContainText("corrupt.jpg");
    await expect(attention).toContainText("could not be decoded");
    await expect(attention).toContainText("notes.png");
    await expect(attention).toContainText("Only .jpg and .jpeg");

    await page.getByLabel("Creative brief").fill(brief);
    await page.getByLabel("Target number of photographs").fill("50");
    await page.getByRole("button", { name: "Save brief and target" }).click();
    await expect(page.getByRole("alert")).toContainText("cannot exceed the 10 accepted photos");

    await saveBrief(page, 3);
    await page.route("**/recommendations", (route) => route.abort("connectionrefused"));
    await analyze(page);
    await expect(page.getByRole("alert")).toContainText("cannot reach its local API");

    await page.unroute("**/recommendations");
    await page.getByRole("button", { name: "Generate proposal" }).click();
    await expect(selectionCount(page, "3 of 3 selected")).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });

  test("the seeded demo is reproducible across fresh projects", async ({ browser }) => {
    const runs: DemoResult[] = [];
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const context = await browser.newContext({ acceptDownloads: true });
      runs.push(await runDemo(await context.newPage()));
      await context.close();
    }
    const [first, second] = runs;
    expect(second.beforeChoices).toEqual(first.beforeChoices);
    expect(second.proposed).toEqual(first.proposed);
    expect(second.csvRows.map((row) => row[1])).toEqual(first.csvRows.map((row) => row[1]));
    expect(second.csvRows[1][0]).not.toEqual(first.csvRows[1][0]);
  });
});

test.describe("SelectIQ Alpha with real OpenCLIP and Groq", () => {
  test.skip(!realAi, "Set SELECTIQ_E2E_REAL_AI=1 and GROQ_API_KEY to run against real models.");
  test.setTimeout(600_000);

  test("produces an AI-informed proposal from real models", async ({ page }) => {
    await runDemo(page);
    await expect(page.getByRole("note")).toContainText("AI-informed proposal");
    await expect(page.getByRole("note")).toContainText("ViT-B-32");
    await expect(page.getByRole("note")).toContainText("groq");
  });
});
