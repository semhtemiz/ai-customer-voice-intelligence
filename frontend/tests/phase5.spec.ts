import {test,expect} from 'playwright/test';
import fs from 'node:fs';
test('real sentiment scope is independent of rating',async({page,request})=>{
 const response=await (await request.get('http://localhost:8000/api/sentiments')).json();
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Sentiment dağılımı · model tahmini'})).toBeVisible();
 for(const bin of response.data.distribution)await expect(page.getByTestId('sentiment-'+bin.sentiment)).toHaveText(bin.reviews.toLocaleString('tr-TR'));
 expect(response.data.classified_count).toBe(22641);
 expect(response.data.distribution.find((bin:{sentiment:string})=>bin.sentiment==='unknown').reviews).toBe(845);
 await page.getByLabel('Sentiment',{exact:true}).selectOption('negative');
 await expect(page.getByTestId('total-reviews')).toHaveText(response.data.distribution.find((bin:{sentiment:string})=>bin.sentiment==='negative').reviews.toLocaleString('tr-TR'));
});
test('topics counts, filter-consistent bounded evidence and empty state',async({page,request})=>{
 await page.goto('/themes');
 const expected=await (await request.get('http://localhost:8000/api/topics')).json();
 await expect(page.getByTestId('candidate_count')).toHaveText(expected.data.candidate_count.toLocaleString('tr-TR'));
 await expect(page.getByTestId('topic_processed_count')).toHaveText(expected.data.topic_processed_count.toLocaleString('tr-TR'));
 await expect(page.locator('article')).not.toHaveCount(0);
 expect(await page.locator('article').count()).toBeLessThanOrEqual(20);
 await page.getByLabel('Rating',{exact:true}).selectOption('1');
 const evidence=await (await request.get('http://localhost:8000/api/topics/sizing/examples?rating=1')).json();
 await expect(page.locator('article')).toHaveCount(evidence.data.length);
 if(evidence.data.length)await expect(page.locator('article').first()).toContainText('Yorum #'+evidence.data[0].review_id);
 await page.getByRole('button',{name:'Shipping',exact:true}).click();
 const shipping=await (await request.get('http://localhost:8000/api/topics/shipping/examples?rating=1')).json();
 await expect(page.locator('article')).toHaveCount(shipping.data.length);
 await page.getByLabel('Yorumlarda ara').fill('NoMatchingReviewUniqueString987654321');
 await expect(page.getByTestId('candidate_count')).toHaveText('0');
 await expect(page.getByText('Bu filtrelerle eşleşen şikâyet adayı yok.')).toBeVisible();
});
test('topics error can retry',async({page})=>{
 let fail=true;await page.route('**/api/topics?**',async route=>{
  if(fail)return route.fulfill({status:503,json:{detail:'Unavailable'}});
  await route.continue();
 });
 await page.goto('/themes');await expect(page.getByRole('heading',{name:'Veriler yüklenemedi'})).toBeVisible();
 fail=false;await page.getByRole('button',{name:'Yeniden dene',exact:true}).click();
 await expect(page.getByTestId('candidate_count')).toBeVisible();
});
for(const width of [1440,768,375])test(`themes responsive ${width}`,async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width,height:1000});await page.goto('/themes');
 await expect(page.getByTestId('topic_processed_count')).toBeVisible();
 await expect(page.locator('article').first()).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 fs.mkdirSync('../screenshots',{recursive:true});
 await page.screenshot({path:`../screenshots/phase5-themes-${width}-light.png`,fullPage:true});
 await page.getByRole('button',{name:'Temayı değiştir'}).click();
 await expect(page.locator('html')).toHaveClass(/dark/);
 await page.screenshot({path:`../screenshots/phase5-themes-${width}-dark.png`,fullPage:true});
 expect(errors).toEqual([]);
});
