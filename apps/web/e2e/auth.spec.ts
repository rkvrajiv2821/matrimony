import { expect, test, type Page } from "@playwright/test";
import en from "@vaibhav/localization/messages/en.json" with { type: "json" };
import ta from "@vaibhav/localization/messages/ta.json" with { type: "json" };
import tanglish from "@vaibhav/localization/messages/ta-Latn.json" with { type: "json" };

const LOCALES = [
  { prefix: "/en", messages: en },
  { prefix: "/ta", messages: ta },
  { prefix: "/tanglish", messages: tanglish },
] as const;

/** A fresh, valid Indian mobile number per test so runs never collide. */
function randomPhone(): string {
  return `9${Math.floor(100_000_000 + Math.random() * 899_999_999)}`;
}

async function register(
  page: Page,
  prefix: string,
  phone = randomPhone(),
  landsOn = prefix,
): Promise<string> {
  await page.goto(`${prefix}/login`);
  await page.getByTestId("phone-input").fill(phone);
  await page.getByTestId("consent-terms").check();
  const devCode = page.getByTestId("dev-code");
  // The same number may still be inside the (shortened, E2E) resend cooldown: retry.
  await expect(async () => {
    await page.getByTestId("send-code").click({ timeout: 2_000 });
    await expect(devCode).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 15_000 });
  const code = (await devCode.textContent())!.match(/\d{6}/)![0];
  await page.getByTestId("otp-input").fill(code);
  await page.getByTestId("verify").click();
  await expect(page).toHaveURL(new RegExp(`${landsOn}/app`));
  return phone;
}

for (const { prefix, messages } of LOCALES) {
  test(`register → OTP → dashboard in ${prefix}`, async ({ page }) => {
    const phone = await register(page, prefix);
    await expect(page.getByTestId("dashboard-heading")).toHaveText(messages.dashboard.welcomeNew);
    await expect(page.getByTestId("masked-phone")).toContainText(`+91******${phone.slice(-4)}`);
    await expect(page.locator("html")).toHaveAttribute("lang", /^(en|ta)/);
  });
}

test("consent is required before a code is sent", async ({ page }) => {
  await page.goto("/en/login");
  await page.getByTestId("phone-input").fill(randomPhone());
  await page.getByTestId("send-code").click();
  await expect(page.getByTestId("form-error")).toHaveText(en.errors.consent_required);
  await expect(page.getByTestId("otp-input")).toHaveCount(0);
});

test("invalid phone and wrong code show localized errors", async ({ page }) => {
  await page.goto("/ta/login");
  await page.getByTestId("phone-input").fill("12345");
  await page.getByTestId("consent-terms").check();
  await page.getByTestId("send-code").click();
  await expect(page.getByTestId("form-error")).toHaveText(ta.errors.invalid_phone);

  await page.getByTestId("phone-input").fill(randomPhone());
  await page.getByTestId("send-code").click();
  const code = (await page.getByTestId("dev-code").textContent())!.match(/\d{6}/)![0];
  const wrong = code === "000000" ? "111111" : "000000";
  await page.getByTestId("otp-input").fill(wrong);
  await page.getByTestId("verify").click();
  await expect(page.getByTestId("form-error")).toHaveText(ta.errors.otp_invalid);
});

test("returning member sees welcome back; logout ends the session", async ({ page }) => {
  const phone = await register(page, "/en");
  await page.getByTestId("logout").click();
  await expect(page).toHaveURL(/\/en$/);
  await page.goto("/en/app");
  await expect(page).toHaveURL(/\/en\/login$/);

  await register(page, "/en", phone);
  await expect(page.getByTestId("dashboard-heading")).toHaveText(en.dashboard.welcomeBack);
});

test("language preference is saved and followed after login", async ({ page }) => {
  const phone = await register(page, "/en");
  await page.goto("/en/app/settings");
  await page.getByTestId("pref-ta").check();
  await expect(page).toHaveURL(/\/ta\/app\/settings$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(ta.settings.title);

  await page.getByTestId("logout").click();
  // Login from the English page lands in the member's saved language.
  await register(page, "/en", phone, "/ta");
});

for (const prefix of ["/en", "/tanglish"]) {
  test(`expired access cookie is refreshed transparently (${prefix})`, async ({ page, context }) => {
    await register(page, prefix);
    await context.clearCookies({ name: "vb_at" });
    await page.goto(`${prefix}/app`);
    await expect(page.getByTestId("dashboard-heading")).toBeVisible();
    const access = (await context.cookies()).find((c) => c.name === "vb_at");
    expect(access?.httpOnly).toBe(true);
  });
}

test("a member can log out another device", async ({ browser }) => {
  const phone = randomPhone();
  const a = await browser.newContext();
  const b = await browser.newContext();
  const pa = await a.newPage();
  const pb = await b.newPage();
  await register(pa, "/en", phone);
  await register(pb, "/en", phone);

  await pa.goto("/en/app/settings");
  const list = pa.getByTestId("session-list");
  await expect(list.getByRole("listitem")).toHaveCount(2);
  await list.getByRole("button", { name: en.settings.logoutDevice }).click();
  await expect(list.getByRole("listitem")).toHaveCount(1);

  await pb.goto("/en/app");
  await expect(pb).toHaveURL(/\/en\/login$/);
  await a.close();
  await b.close();
});

test("public pages render in every language and the switcher keeps the path", async ({ page }) => {
  await page.goto("/en/safety");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(en.pages.safety.title);
  await page.getByTestId("language-switcher").first().selectOption("ta-Latn");
  await expect(page).toHaveURL(/\/tanglish\/safety$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(tanglish.pages.safety.title);
});

test("tokens are never exposed to page JavaScript", async ({ page }) => {
  await register(page, "/en");
  const visible = await page.evaluate(() => document.cookie);
  expect(visible).not.toContain("vb_at");
  expect(visible).not.toContain("vb_rt");
});

test("cross-origin POSTs to the BFF are refused", async ({ request }) => {
  const r = await request.post("/api/auth/request-otp", {
    headers: { origin: "https://evil.example" },
    data: { phone: randomPhone() },
  });
  expect(r.status()).toBe(403);
});

test("no horizontal scrolling at phone width, signed out or in", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  const noOverflow = async () =>
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
    ).toBeLessThanOrEqual(0);
  for (const path of ["/en", "/ta", "/tanglish/login", "/ta/how-it-works"]) {
    await page.goto(path);
    await noOverflow();
  }
  await register(page, "/ta");
  for (const path of ["/ta/app", "/ta/app/settings", "/tanglish/app/settings"]) {
    await page.goto(path);
    await noOverflow();
  }
});
