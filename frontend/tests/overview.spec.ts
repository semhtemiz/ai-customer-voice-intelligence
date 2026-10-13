import { test, expect } from "playwright/test";
import fs from "node:fs";
test("real metrics, filters, reset and shared navigation", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByTestId("total-reviews")).toHaveText("23.486");
  await page.getByLabel("Departman", { exact:true }).selectOption("Tops");
  await page.getByLabel("Rating", { exact:true }).selectOption("1");
  const filtered = await (await request.get("http://localhost:8000/api/overview?department=Tops&rating=1")).json();
  await expect(page.getByTestId("total-reviews")).toHaveText(filtered.data.total_reviews.toLocaleString("tr-TR"));
  await page.getByRole("link", { name:"Veri Kalitesi", exact:true }).click();
  await expect(page.getByRole("heading", { name:"Genel import raporu" })).toBeVisible();
  await expect(page.getByLabel("Departman", { exact:true })).toHaveValue("Tops");
  await page.getByRole("link", { name:"Overview", exact:true }).click();
  await expect(page.getByLabel("Rating", { exact:true })).toHaveValue("1");
  await page.getByRole("button", { name:"Filtreleri temizle" }).click();
  await expect(page.getByTestId("total-reviews")).toHaveText("23.486");
});
test("empty result, loading, error and retry", async ({ page }) => {
  let fail = true;
  await page.route("**/api/overview?**", async route => {
    await new Promise(resolve => setTimeout(resolve, 300));
    if (fail) await route.fulfill({ status:503, json:{detail:"Database is not ready"} });
    else await route.continue();
  });
  await page.goto("/");
  await expect(page.getByRole("status", { name:"Analiz yükleniyor" })).toBeVisible();
  await expect(page.getByRole("heading", { name:"Analiz yüklenemedi" })).toBeVisible();
  fail = false;
  await page.getByRole("button", { name:"Yeniden dene" }).click();
  await expect(page.getByTestId("total-reviews")).toHaveText("23.486");
  await page.getByLabel("Yorumlarda ara").fill("NoMatchingReviewUniqueString987654321");
  await expect(page.getByRole("heading", { name:"Bu filtrelerle eşleşen yorum yok" })).toBeVisible();
  await page.getByRole("button", { name:"Filtreleri sıfırla" }).click();
  await expect(page.getByTestId("total-reviews")).toHaveText("23.486");
});
test("obsolete responses cannot overwrite active filters", async ({ page }) => {
  await page.route("**/api/overview?**", async route => {
    if (new URL(route.request().url()).searchParams.get("rating") === "1") {
      const response = await route.fetch();
      await new Promise(resolve => setTimeout(resolve, 700));
      await route.fulfill({ response }).catch(() => {});
    } else await route.continue();
  });
  await page.goto("/");
  await expect(page.getByTestId("total-reviews")).toHaveText("23.486");
  await page.getByLabel("Rating", { exact:true }).selectOption("1");
  await page.getByLabel("Rating", { exact:true }).selectOption("5");
  await expect(page.getByTestId("total-reviews")).toHaveText("13.131");
  await page.waitForTimeout(900);
  await expect(page.getByTestId("total-reviews")).toHaveText("13.131");
});
for (const width of [1440, 768, 375]) {
  test(`responsive ${width}, navigation, theme and screenshot`, async ({ page }) => {
    const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
    await page.setViewportSize({ width, height:1000 });
    await page.goto("/");
    await expect(page.getByTestId("total-reviews")).toHaveText("23.486");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    if (width < 768) {
      await page.getByRole("button", { name:"Menüyü aç/kapat" }).click();
      await expect(page.getByRole("link", { name:"Şikâyet Temaları", exact:true })).toBeVisible();
      await page.keyboard.press("Escape");
    }
    await page.keyboard.press("Tab");
    await page.getByRole("button", { name:"Temayı değiştir" }).click();
    await expect(page.locator("html")).toHaveClass(/dark/);
    fs.mkdirSync("../screenshots", { recursive:true });
    await page.screenshot({ path:`../screenshots/phase3-overview-${width}-dark.png`, fullPage:true });
    await page.getByRole("button", { name:"Temayı değiştir" }).click();
    await expect(page.locator("html")).not.toHaveClass(/dark/);
    await page.screenshot({ path:`../screenshots/phase3-overview-${width}-light.png`, fullPage:true });
    expect(errors).toEqual([]);
  });
}
test("keyboard access and unavailable metrics remain explicit", async ({ page }) => {
  // Simulate unavailable rating/recommendation values without adding app fallbacks.
  await page.route("**/api/overview?**", async route => {
    const response = await route.fetch(); const body = await response.json();
    body.data = { ...body.data, valid_rating_count:0, valid_recommendation_count:0,
      avg_rating:null, recommendation_rate_pct:null, low_rating_rate_pct:null };
    await route.fulfill({ response, json:body });
  });
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name:"İçeriğe geç" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await expect(page.getByTestId("average-rating")).toHaveText("Veri yok");
  await expect(page.getByTestId("recommendation-rate")).toHaveText("Veri yok");
  await expect(page.getByTestId("low-rating-share")).toHaveText("Veri yok");
});
