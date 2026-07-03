import { test, expect } from "@playwright/test";

const BACKEND_URL =
  process.env.E2E_BACKEND_URL ||
  process.env.VITE_BACKEND_URL ||
  process.env.VITE_API_BASE_URL ||
  "http://localhost:8000";
const USER_PREFIX = process.env.E2E_TEST_USER_PREFIX || "e2e";

function uniqueSuffix() {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function createLegacyCredentials() {
  const suffix = uniqueSuffix();
  return {
    identifier: `${USER_PREFIX}_${suffix}`,
    password: "E2eSmoke!12345",
    firstTimeExpected: true,
    requiresRegistration: true,
  };
}

function resolveSupabaseCredentials() {
  const fixedEmail = process.env.E2E_SUPABASE_TEST_EMAIL;
  const fixedPassword = process.env.E2E_SUPABASE_TEST_PASSWORD;
  if (fixedEmail && fixedPassword) {
    return {
      identifier: fixedEmail,
      password: fixedPassword,
      firstTimeExpected: false,
      requiresRegistration: false,
      description: "existing test account",
    };
  }

  const signUpEnabled = process.env.E2E_SUPABASE_SIGNUP_ENABLED === "true";
  const emailDomain = process.env.E2E_SUPABASE_TEST_EMAIL_DOMAIN;
  const generatedPassword = process.env.E2E_SUPABASE_TEST_PASSWORD;
  if (signUpEnabled && emailDomain && generatedPassword) {
    const suffix = uniqueSuffix();
    return {
      identifier: `${USER_PREFIX}_${suffix}@${emailDomain}`,
      password: generatedPassword,
      firstTimeExpected: true,
      requiresRegistration: true,
      description: "generated signup account",
    };
  }

  return null;
}

async function isBackendAvailable() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

async function detectAuthMode(page) {
  const providerBadge = page.locator("text=Supabase Auth").or(page.locator("text=Legacy Auth"));
  await expect(providerBadge.first()).toBeVisible();
  const providerText = await providerBadge.first().textContent();
  return providerText?.includes("Supabase") ? "supabase" : "legacy";
}

async function authenticate(page, authMode) {
  if (authMode === "legacy") {
    const credentials = createLegacyCredentials();
    const form = page.locator("form");

    await page.getByRole("button", { name: "Register" }).first().click();
    await page.getByPlaceholder("your username").fill(credentials.identifier);
    await form.locator('input[type="password"]').fill(credentials.password);
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText(/Account created!/)).toBeVisible();

    await page.getByRole("button", { name: "Log In" }).first().click();
    await page.getByPlaceholder("your username").fill(credentials.identifier);
    await form.locator('input[type="password"]').fill(credentials.password);
    await form.getByRole("button", { name: "Log In" }).click();
    return credentials;
  }

  const credentials = resolveSupabaseCredentials();
  test.skip(
    !credentials,
    "Supabase smoke auth requires E2E_SUPABASE_TEST_EMAIL/E2E_SUPABASE_TEST_PASSWORD or generated signup env."
  );

  if (credentials.requiresRegistration) {
    const form = page.locator("form");
    await page.getByRole("button", { name: "Register" }).first().click();
    await page.getByPlaceholder("you@example.com").fill(credentials.identifier);
    await form.locator('input[type="password"]').fill(credentials.password);
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText(/Account created!/)).toBeVisible();
    await page.getByRole("button", { name: "Log In" }).first().click();
  }

  const form = page.locator("form");
  await page.getByPlaceholder("you@example.com").fill(credentials.identifier);
  await form.locator('input[type="password"]').fill(credentials.password);
  await form.getByRole("button", { name: "Log In" }).click();
  return credentials;
}

async function finishOnboardingIfPresent(page, firstTimeExpected) {
  await page.waitForURL(/\/(onboarding|dashboard)/, { timeout: 20_000 });

  if (!firstTimeExpected) {
    if (page.url().includes("/onboarding")) {
      await page.getByRole("button", { name: /Back to dashboard|Skip for now/i }).first().click();
      await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
    }
    return;
  }

  await expect(page).toHaveURL(/\/onboarding/);
  await expect(page.getByText("First-Time Setup")).toBeVisible();
  await expect(page.getByText(/Set up the app around your real network/i)).toBeVisible();
  await page.getByRole("button", { name: /Skip for now/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
}

test("login/register page loads and auth mode badge is visible", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "NetworkingAssistant" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Log In" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Register" }).first()).toBeVisible();
  await expect(page.locator("text=Supabase Auth").or(page.locator("text=Legacy Auth")).first()).toBeVisible();
});

test.describe.serial("authenticated smoke", () => {
  let backendAvailable = false;

  test.beforeAll(async () => {
    backendAvailable = await isBackendAvailable();
  });

  test("auth, dashboard, onboarding/profile fallback, menus, custom select, and logout", async ({ page }) => {
    test.skip(!backendAvailable, `Local backend is not reachable at ${BACKEND_URL}`);

    await page.goto("/login");
    const authMode = await detectAuthMode(page);
    const credentials = await authenticate(page, authMode);

    await finishOnboardingIfPresent(page, credentials.firstTimeExpected);

    await expect(page.getByText("Command Center")).toBeVisible();
    if (credentials.firstTimeExpected) {
      await expect(page.locator("text=Open onboarding").or(page.locator("text=Resume onboarding")).first()).toBeVisible();
    }

    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible();
    if (credentials.firstTimeExpected) {
      await expect(page.getByText(/Set up your profile|Edit profile/)).toBeVisible();
      await expect(page.getByText(/Something went wrong/i)).toHaveCount(0);
    }

    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Notifications" }).click();
    await expect(page.getByText("Notification Center")).toBeVisible();
    await page.mouse.click(20, 20);

    await page.getByRole("button", { name: "Account menu" }).click();
    await expect(page.getByText("Account menu")).toBeVisible();
    await page.mouse.click(20, 20);

    await page.goto("/contacts");
    const companyFilter = page.getByRole("button", { name: /All companies/i });
    await companyFilter.click();
    await expect(page.getByRole("listbox")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("listbox")).toHaveCount(0);

    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("button", { name: "Logout" }).click();
    await page.waitForURL(/\/login/, { timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Log In" })).toBeVisible();
  });
});
