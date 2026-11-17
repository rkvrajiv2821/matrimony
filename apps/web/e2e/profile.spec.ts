import { expect, test, type Browser, type Page } from "@playwright/test";
import en from "@vaibhav/localization/messages/en.json" with { type: "json" };
import ta from "@vaibhav/localization/messages/ta.json" with { type: "json" };
import tanglish from "@vaibhav/localization/messages/ta-Latn.json" with { type: "json" };
import { execFileSync } from "node:child_process";
import path from "node:path";

const API_DIR = path.resolve(__dirname, "../../../services/api");

function randomPhone(): string {
  return `9${Math.floor(100_000_000 + Math.random() * 899_999_999)}`;
}

async function login(page: Page, prefix: string, phone = randomPhone()): Promise<string> {
  await page.goto(`${prefix}/login`);
  await page.getByTestId("phone-input").fill(phone);
  await page.getByTestId("consent-terms").check();
  const devCode = page.getByTestId("dev-code");
  await expect(async () => {
    await page.getByTestId("send-code").click({ timeout: 2_000 });
    await expect(devCode).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 15_000 });
  const code = (await devCode.textContent())!.match(/\d{6}/)![0];
  await page.getByTestId("otp-input").fill(code);
  await page.getByTestId("verify").click();
  await expect(page).toHaveURL(new RegExp(`${prefix}/app`));
  return phone;
}

/** A real JPEG to upload: a screenshot of the current page. */
async function samplePhoto(page: Page): Promise<Buffer> {
  return page.screenshot({ type: "jpeg", quality: 70 });
}

async function save(page: Page, nextUrl: RegExp) {
  await page.getByTestId("step-save").click();
  await expect(page).toHaveURL(nextUrl);
}

/** Local moderation shortcut (the admin portal arrives in Phase 5). */
function approve(profileId: string) {
  execFileSync("uv", ["run", "python", "-m", "app.cli", "approve-profile", profileId], {
    cwd: API_DIR,
    stdio: "pipe",
    env: process.env,
  });
}

test("create, complete, submit and get approved", async ({ page }) => {
  test.setTimeout(90_000);
  await login(page, "/en");
  await page.getByTestId("create-profile-cta").click();
  await page.getByTestId("gender-female").check();
  await page.getByTestId("field-subject_name").fill("Priya Sundaram");
  await page.getByTestId("create-profile").click();
  await expect(page).toHaveURL(/\/en\/app\/profile\/[0-9a-f-]+\/edit\/basic$/);
  const profileId = page.url().match(/profile\/([0-9a-f-]+)\//)![1]!;

  // Basic
  await page.getByTestId("field-display_name").fill("Priya S.");
  await page.getByTestId("field-date_of_birth").fill("1997-06-15");
  await page.getByTestId("field-height_cm").selectOption("160");
  await page.getByTestId("field-marital_status").selectOption("never_married");
  await page.getByTestId("field-district_code").selectOption("tn-madurai");
  await page.getByTestId("field-city_code").selectOption("tn-madurai-city");
  await save(page, /edit\/community$/);
  // Community → Education → Career
  await page.getByTestId("field-sub_community_code").selectOption("sub_a");
  await save(page, /edit\/education$/);
  await page.getByTestId("field-qualification").selectOption("bachelors");
  await save(page, /edit\/career$/);
  await page.getByTestId("field-employment_type").selectOption("government");
  await page.getByTestId("field-occupation").fill("Teacher");
  await save(page, /edit\/family$/);
  await page.getByTestId("field-family_type").selectOption("joint");
  await save(page, /edit\/lifestyle$/);
  await page.getByTestId("field-diet").selectOption("vegetarian");
  await page.getByTestId("languages-english").check();
  await page.getByTestId("field-about_me").fill("I teach mathematics and enjoy Carnatic music.");
  await save(page, /edit\/photos$/);

  // Photos
  await page.getByTestId("photo-input").setInputFiles({
    name: "me.jpg",
    mimeType: "image/jpeg",
    buffer: await samplePhoto(page),
  });
  await expect(page.getByTestId("photo-grid").getByRole("listitem")).toHaveCount(1, { timeout: 15_000 });
  await expect(page.getByTestId("photo-grid")).toContainText(en.photos.status.pending);
  const thumb = page.getByTestId("photo-grid").locator("img").first();
  await expect(thumb).toHaveJSProperty("complete", true);
  expect(await thumb.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  await save(page, /edit\/preferences$/);

  // Preferences
  await page.getByTestId("importance-age-must").click();
  await page.getByTestId("pref-marital-never_married").check();
  await save(page, new RegExp(`/profile/${profileId}$`));

  // Overview → submit
  await expect(page.getByTestId("profile-status")).toHaveAttribute("data-status", "draft");
  await page.getByTestId("submit-profile").click();
  await expect(page.getByTestId("profile-status")).toHaveAttribute("data-status", "submitted");

  approve(profileId);
  await page.reload();
  await expect(page.getByTestId("profile-status")).toHaveAttribute("data-status", "approved");
  await expect(page.getByTestId("status-body")).toHaveText(en.profile.statusBody.approved);

  // Preview shows exactly what members see: no birth date, no full surname.
  await page.goto(`/en/app/profile/${profileId}/preview`);
  const card = page.getByTestId("member-card");
  await expect(page.getByTestId("member-name")).toHaveText("Priya S.");
  await expect(card).toContainText("Teacher");
  await expect(card).not.toContainText("1997");
  await expect(card).not.toContainText("Sundaram");
  await expect(card.locator("img")).toHaveCount(1);
});

test("submit is disabled until required sections are done", async ({ page }) => {
  await login(page, "/en");
  await page.goto("/en/app/profile/new");
  await page.getByTestId("field-subject_name").fill("Arun");
  await page.getByTestId("create-profile").click();
  await expect(page).toHaveURL(/edit\/basic$/);
  await page.goto(page.url().replace(/\/edit\/basic$/, ""));
  await expect(page.getByTestId("submit-profile")).toBeDisabled();
  await expect(page.getByText(en.profile.completionItems.photo)).toBeVisible();
});

test("under-18 and contact details are refused with localized messages", async ({ page }) => {
  await login(page, "/tanglish");
  await page.goto("/tanglish/app/profile/new");
  await page.getByTestId("field-subject_name").fill("Karthik");
  await page.getByTestId("gender-male").check();
  await page.getByTestId("create-profile").click();
  await expect(page).toHaveURL(/edit\/basic$/);
  const year = new Date().getFullYear() - 16;
  await page.getByTestId("field-display_name").fill("Karthik R.");
  await page.getByTestId("field-date_of_birth").fill(`${year}-01-10`);
  await page.getByTestId("field-height_cm").selectOption("170");
  await page.getByTestId("field-marital_status").selectOption("never_married");
  await page.getByTestId("step-save").click();
  await expect(page.getByTestId("form-error")).toHaveText(tanglish.errors.underage);

  await page.goto(page.url().replace(/basic$/, "lifestyle"));
  await page.getByTestId("field-about_me").fill("Call me on 98765 43210");
  await page.getByTestId("step-save").click();
  await expect(page.getByTestId("form-error")).toHaveText(tanglish.errors.contact_details_not_allowed);
});

test("wizard renders in Tamil", async ({ page }) => {
  await login(page, "/ta");
  await page.goto("/ta/app/profile/new");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(ta.profile.createTitle);
  await page.getByTestId("field-subject_name").fill("மீனா");
  await page.getByTestId("create-profile").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(ta.profile.sections.basic);
  await expect(page.getByTestId("field-district_code").locator("option", { hasText: "மதுரை" })).toHaveCount(1);
});

async function newPage(browser: Browser) {
  const ctx = await browser.newContext();
  return { ctx, page: await ctx.newPage() };
}

test("a parent's profile for an adult needs the adult's consent", async ({ browser }) => {
  test.setTimeout(60_000);
  const daughterPhone = randomPhone();
  const parent = await newPage(browser);
  const daughter = await newPage(browser);

  await login(parent.page, "/en");
  await parent.page.goto("/en/app/profile/new");
  await parent.page.getByTestId("created_for-daughter").check();
  await parent.page.getByTestId("field-subject_name").fill("Kavya");
  await parent.page.getByTestId("field-subject_phone").fill(daughterPhone);
  await parent.page.getByTestId("create-profile").click();
  await expect(parent.page.getByTestId("awaiting-consent")).toBeVisible();
  const profileUrl = parent.page.url();
  // The parent can't fill anything in yet.
  await parent.page.goto(`${profileUrl}/edit/basic`);
  await parent.page.getByTestId("field-display_name").fill("Kavya");
  await parent.page.getByTestId("field-date_of_birth").fill("1999-02-02");
  await parent.page.getByTestId("field-height_cm").selectOption("158");
  await parent.page.getByTestId("gender-female").check();
  await parent.page.getByTestId("field-marital_status").selectOption("never_married");
  await parent.page.getByTestId("step-save").click();
  await expect(parent.page.getByTestId("form-error")).toHaveText(en.errors.subject_consent_pending);

  await login(daughter.page, "/en", daughterPhone);
  const invite = daughter.page.getByTestId("invitation");
  await expect(invite).toBeVisible();
  await invite.getByTestId("scope-manage_photos").uncheck();
  await invite.getByTestId("accept-invitation").click();
  await expect(daughter.page).toHaveURL(/\/en\/app\/profile\/[0-9a-f-]+$/);
  await expect(daughter.page.getByText(en.profile.roleOwner, { exact: true })).toBeVisible();

  await parent.page.goto("/en/app");
  await expect(parent.page.getByTestId("profile-card")).toContainText(en.profile.roleDelegate);

  await parent.ctx.close();
  await daughter.ctx.close();
});

test("declining an invitation closes the draft", async ({ browser }) => {
  const daughterPhone = randomPhone();
  const parent = await newPage(browser);
  const daughter = await newPage(browser);
  await login(parent.page, "/en");
  await parent.page.goto("/en/app/profile/new");
  await parent.page.getByTestId("created_for-son").check();
  await parent.page.getByTestId("field-subject_name").fill("Vikram");
  await parent.page.getByTestId("field-subject_phone").fill(daughterPhone);
  await parent.page.getByTestId("create-profile").click();
  await expect(parent.page.getByTestId("awaiting-consent")).toBeVisible();

  await login(daughter.page, "/en", daughterPhone);
  await daughter.page.getByTestId("decline-invitation").click();
  await expect(daughter.page.getByTestId("invitation")).toHaveCount(0);

  await parent.page.goto("/en/app");
  await expect(parent.page.getByTestId("profile-card")).toHaveCount(0);
  await parent.ctx.close();
  await daughter.ctx.close();
});

test("profile pages have no horizontal scrolling at phone width", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await login(page, "/ta");
  await page.goto("/ta/app/profile/new");
  await page.getByTestId("field-subject_name").fill("மீனா");
  await page.getByTestId("create-profile").click();
  await expect(page).toHaveURL(/edit\/basic$/);
  const base = page.url().replace(/\/edit\/basic$/, "");
  for (const p of ["", "/edit/basic", "/edit/career", "/edit/lifestyle", "/edit/photos", "/edit/preferences", "/preview", "/helpers"]) {
    await page.goto(base + p);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `overflow on ${p || "overview"}`).toBeLessThanOrEqual(0);
  }
});
