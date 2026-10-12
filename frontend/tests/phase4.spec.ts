import { test, expect } from "playwright/test";
import fs from "node:fs";
const ids = async (page: import("playwright/test").Page) => page.locator("tr[data-review-id]").evaluateAll(rows => rows.map(row => row.getAttribute("data-review-id")));
test("reviews pagination, filters, keyboard detail and selection invalidation", async ({ page,request }) => {
  await page.goto("/reviews");
  await expect(page.getByTestId("reviews-total")).toHaveText("23.486");
  const first = await ids(page); expect(first).toHaveLength(20);
  await page.getByRole("button",{name:"Sonraki",exact:true}).click();
  await expect(page.getByTestId("page-info")).toContainText("Sayfa 2 /");
  const second = await ids(page); expect(second).toHaveLength(20);
  expect(second.some(id => first.includes(id))).toBeFalsy();
  await page.getByLabel("Rating",{exact:true}).selectOption("1");
  await expect(page.getByTestId("page-info")).toContainText("Sayfa 1 /");
  await page.getByLabel("Departman",{exact:true}).selectOption("Tops");
  const expected=await (await request.get("http://localhost:8000/api/reviews?rating=1&department=Tops")).json();
  await expect(page.getByTestId("reviews-total")).toHaveText(expected.total.toLocaleString("tr-TR"));
  const trigger=page.getByRole("button",{name:/Yorum #\d+ ayrıntısını aç/}).first();
  await trigger.focus(); await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("heading",{name:"Topic etiketleri"})).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  // Programmatic shared-filter updates also invalidate an open detail panel.
  await page.getByLabel("Rating",{exact:true}).selectOption("5",{force:true});
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByLabel("Yorumlarda ara").fill("NoMatchingReviewUniqueString987654321");
  await expect(page.getByRole("heading",{name:"Bu filtrelerle eşleşen yorum yok"})).toBeVisible();
  await page.getByRole("button",{name:"Filtreleri sıfırla",exact:true}).click();
  await expect(page.getByTestId("reviews-total")).toHaveText("23.486");
});
test("quality keeps import scope separate from filtered scope", async ({ page,request }) => {
  await page.goto("/data-quality");
  await expect(page.getByTestId("import-total")).toHaveText("23.486");
  await expect(page.getByTestId("import-duplicates")).toHaveText("21");
  const checksum=await page.getByTestId("dataset-checksum").textContent();
  await page.getByLabel("Departman",{exact:true}).selectOption("Unknown");
  const expected=await (await request.get("http://localhost:8000/api/data-quality?department=Unknown")).json();
  await expect(page.getByTestId("filtered-quality-total")).toHaveText(expected.data.filtered_quality.review_count.toLocaleString("tr-TR"));
  await expect(page.getByTestId("import-total")).toHaveText("23.486");
  await expect(page.getByTestId("dataset-checksum")).toHaveText(checksum!);
  await expect(page.getByTestId("quality-missing_department_count")).toHaveText("14");
  await page.getByLabel("Yorumlarda ara").fill("NoMatchingReviewUniqueString987654321");
  await expect(page.getByTestId("filtered-quality-total")).toHaveText("0");
  await expect(page.getByTestId("import-total")).toHaveText("23.486");
  await expect(page.getByText(/genel import raporu gösterilmeye devam eder/)).toBeVisible();
});
for (const path of ["reviews","data-quality"]) {
  test(`${path} error, retry and obsolete responses`,async ({page}) => {
    const endpoint=path==="reviews" ? "reviews" : "data-quality";
    let fail=true;
    await page.route(`**/api/${endpoint}?**`,async route => {
      if(fail) return route.fulfill({status:503,json:{detail:"Database is not ready"}});
      if(new URL(route.request().url()).searchParams.get("rating")==="1") {
        const response=await route.fetch(); await new Promise(resolve=>setTimeout(resolve,600));
        return route.fulfill({response}).catch(()=>{});
      }
      await route.continue();
    });
    await page.goto('/'+path);
    await expect(page.getByRole("heading",{name:"Veriler yüklenemedi"})).toBeVisible();
    fail=false;await page.getByRole("button",{name:"Yeniden dene",exact:true}).click();
    const target=page.getByTestId(path==="reviews" ? "reviews-total" : "filtered-quality-total");
    await expect(target).toHaveText("23.486");
    await page.getByLabel("Rating",{exact:true}).selectOption("1");
    await page.getByLabel("Rating",{exact:true}).selectOption("5");
    await expect(target).toHaveText("13.131");
    await page.waitForTimeout(800);await expect(target).toHaveText("13.131");
  });
}
test("review page beyond changed total has a recovery action",async ({page})=>{
  await page.route("**/api/reviews?**",async route=>{
    const response=await route.fetch();const body=await response.json();
    if(new URL(route.request().url()).searchParams.get("page")==="2") {
      body.items=[];body.total=10;body.total_pages=1;body.meta.matched_review_count=10;
    }
    await route.fulfill({response,json:body});
  });
  await page.goto('/reviews');await expect(page.getByTestId('reviews-total')).toHaveText('23.486');
  await page.getByRole('button',{name:'Sonraki',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Bu sayfada yorum yok'})).toBeVisible();
  await page.getByRole('button',{name:'İlk sayfa',exact:true}).click();
  await expect(page.locator('tr[data-review-id]')).toHaveCount(20);
});
for (const width of [1440,768,375]) {
  test(`phase4 responsive ${width}`,async ({page})=>{
    const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
    await page.setViewportSize({width,height:1000});fs.mkdirSync('../screenshots',{recursive:true});
    for(const path of ['reviews','data-quality']) {
      await page.goto('/'+path);
      await expect(page.getByTestId(path==='reviews' ? 'reviews-total' : 'import-total')).toHaveText('23.486');
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
      await page.screenshot({path:`../screenshots/phase4-${path}-${width}-light.png`,fullPage:true});
      await page.getByRole('button',{name:'Temayı değiştir'}).click();
      await expect(page.locator('html')).toHaveClass(/dark/);
      await page.screenshot({path:`../screenshots/phase4-${path}-${width}-dark.png`,fullPage:true});
      await page.getByRole('button',{name:'Temayı değiştir'}).click();
    }
    expect(errors).toEqual([]);
  });
}
