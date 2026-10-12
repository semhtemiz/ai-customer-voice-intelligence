import {test,expect,type Page} from 'playwright/test';
async function mockTranslations(page:Page,options:{fail?:boolean;delay?:number}={}){
 await page.route('**/api/reviews/translations',async route=>{
  await new Promise(resolve=>setTimeout(resolve,options.delay??80));
  if(options.fail)return route.fulfill({status:502,json:{detail:'Unavailable'}});
  const ids=route.request().postDataJSON().review_ids as number[];
  expect(ids.length).toBeLessThanOrEqual(5);
  return route.fulfill({json:{items:ids.map(id=>({review_id:id,title:`Türkçe başlık ${id}`,review_text:`Türkçe yorum ${id}: Beden ve kumaş hakkındaki geri bildirim.`})),language:'tr',model:'test'}});
 });
}
test('TR/EN updates review table and details, keeping source accessible',async({page})=>{
 await mockTranslations(page);await page.goto('/reviews');await expect(page.getByTestId('reviews-total')).toBeVisible();
 const row=page.locator('tr[data-review-id]').first();const id=await row.getAttribute('data-review-id');const source=(await row.textContent())!;
 await page.getByRole('button',{name:'Türkçe yorumları göster',exact:true}).click();
 await expect(page.getByText(/Türkçe çeviriler hazırlanıyor…/)).toBeVisible();
 await expect(row).toContainText(`Türkçe yorum ${id}`);
 await expect(page.getByText(/Türkçe çeviriler hazırlanıyor…/)).not.toBeVisible({timeout:10000});
 await row.getByRole('button').click();const dialog=page.getByRole('dialog');await expect(dialog).toContainText(`Türkçe yorum ${id}`);
 await dialog.getByRole('button',{name:'İngilizce yorumları göster',exact:true}).click();await expect(row).toHaveText(source);
 await page.keyboard.press('Escape');await expect(row.getByRole('button')).toBeFocused();
});
test('theme evidence has its own TR/EN controls',async({page})=>{
 await mockTranslations(page);await page.goto('/themes');const article=page.locator('article').first();await expect(article).toBeVisible();const source=(await article.textContent())!;
 await page.getByRole('button',{name:'Türkçe yorumları göster',exact:true}).click();await expect(article).toContainText('Türkçe yorum');
 await page.getByRole('button',{name:'İngilizce yorumları göster',exact:true}).click();await expect(article).toHaveText(source);
});
test('translation error preserves English source and retry works',async({page})=>{
 const options={fail:true};await mockTranslations(page,options);await page.goto('/reviews');await expect(page.getByTestId('reviews-total')).toBeVisible();const row=page.locator('tr[data-review-id]').first();const source=(await row.textContent())!;
 await page.getByRole('button',{name:'Türkçe yorumları göster',exact:true}).click();await expect(page.getByRole('alert').filter({hasText:'İngilizce kaynak olarak'})).toContainText('İngilizce kaynak olarak');await expect.poll(async()=>(await row.textContent())?.replace('EN · kaynak','')).toBe(source);
 options.fail=false;await page.getByRole('button',{name:'Çeviriyi yeniden dene'}).click();await expect(row).toContainText('Türkçe yorum');
});
test('late translation cannot overwrite EN; mobile controls fit',async({page})=>{
 await mockTranslations(page,{delay:400});await page.setViewportSize({width:375,height:900});await page.goto('/reviews');await expect(page.getByTestId('reviews-total')).toBeVisible();const row=page.locator('tr[data-review-id]').first();const source=(await row.textContent())!;
 await page.getByRole('button',{name:'Türkçe yorumları göster',exact:true}).click();await page.getByRole('button',{name:'İngilizce yorumları göster',exact:true}).click();await page.waitForTimeout(700);await expect(row).toHaveText(source);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await expect(page.getByRole('button',{name:'İngilizce yorumları göster',exact:true})).toHaveAttribute('aria-pressed','true');
});
