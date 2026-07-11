import { test, expect } from "@playwright/test";

test.describe("Project selector", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/portfolio/projects", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ventures: [
            {
              id: "advoi-system",
              name: "ADVoi System",
              status: "active",
              fleet_slug: "advoi",
              squads: ["platform-squad"],
              functions: [
                {
                  id: "fleet_status",
                  label: "Option A: Fleet status",
                  kind: "frame",
                  frame_id: "fleet_status",
                },
              ],
            },
            {
              id: "gem-dev-shop",
              name: "Gem Dev Shop",
              status: "active",
              fleet_slug: "gem-dev-shop",
              squads: ["venture-squad"],
              functions: [],
            },
          ],
          active_venture_id: "advoi-system",
        }),
      });
    });

    await page.route("**/api/portfolio/active", async (route) => {
      const body = route.request().postDataJSON() as {
        venture_id?: string;
        function_id?: string | null;
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          venture_id: body.venture_id,
          venture_name: body.venture_id === "gem-dev-shop" ? "Gem Dev Shop" : "ADVoi System",
          frame_id: body.function_id ?? null,
        }),
      });
    });
  });

  test("dropdown selects and activates a project", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("project-selector")).toBeVisible();
    await page.getByTestId("project-selector-trigger").click();
    await page.getByTestId("project-option-gem-dev-shop").click();
    await expect(page.getByTestId("project-selector-trigger")).toContainText("Gem Dev Shop");
  });

  test("function chip scopes active project function", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("project-selector-trigger").click();
    await page.getByTestId("project-function-fleet_status").click();
    await expect(page.getByTestId("project-selector-trigger")).toContainText("Fleet status");
  });
});