import {test,expect} from 'playwright/test';
import fs from 'node:fs';
test('filtered rules summary and evidence links stay aligned',async({page,request})=>{
 await page.goto('/insights');await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.getByTestId('insight-source')).toHaveText(/Rules özeti|LLM seçimi/);
 await expect(page.getByRole('heading',{name:'Temel bulgular'})).toBeVisible();
 await page.getByRole('link',{name:'Toplam yorum',exact:true}).first().click();
 await expect(page.locator('#e_total_reviews')).toBeVisible();
 await page.getByLabel('Rating',{exact:true}).selectOption('1');
 await expect(page.getByRole('heading',{name:'Filtreler değişti'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Temel bulgular'})).not.toBeVisible();
 const expected=await (await request.post('http://localhost:8000/api/insights',{data:{rating:1}})).json();
 await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.locator('#e_total_reviews')).toContainText(expected.meta.matched_review_count.toLocaleString('tr-TR'));
 await page.getByLabel('Yorumlarda ara').fill('NoMatchingReviewUniqueString987654321');
 await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.getByTestId('insight-source')).toHaveText('Boş veri');
 await expect(page.getByRole('heading',{name:'Temel bulgular'})).not.toBeVisible();
});
test('error retry and obsolete summary response',async({page})=>{
 let fail=true;await page.route('**/api/insights',async route=>{
  if(fail)return route.fulfill({status:503,json:{detail:'Unavailable'}});
  const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,400));await route.fulfill({response}).catch(()=>{});
 });
 await page.goto('/insights');await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Özet üretilemedi'})).toBeVisible();
 fail=false;await page.getByRole('button',{name:'Yeniden dene',exact:true}).click();
 await expect(page.getByRole('status',{name:'Özet üretiliyor'})).toBeVisible();
 await page.getByLabel('Rating',{exact:true}).selectOption('1');
 await page.waitForTimeout(500);
 await expect(page.getByRole('heading',{name:'Filtreler değişti'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Temel bulgular'})).not.toBeVisible();
 await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.getByTestId('insight-source')).toHaveText(/Rules özeti|LLM seçimi/);
});
for(const width of [1440,768,375])test(`insights responsive ${width}`,async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width,height:1000});await page.goto('/insights');
 await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.getByTestId('insight-source')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 fs.mkdirSync('../screenshots',{recursive:true});
 await page.screenshot({path:`../screenshots/phase6-insights-${width}-light.png`,fullPage:true});
 await page.getByRole('button',{name:'Temayı değiştir'}).click();
 await expect(page.locator('html')).toHaveClass(/dark/);
 await page.screenshot({path:`../screenshots/phase6-insights-${width}-dark.png`,fullPage:true});
 expect(errors).toEqual([]);
});
