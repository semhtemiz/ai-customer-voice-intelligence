import {test,expect} from 'playwright/test';
test('language persists across screens and reload; only nearby reviews are translated',async({page})=>{
 const requested:number[]=[];
 await page.route('**/api/reviews/translations',route=>{
  const ids=route.request().postDataJSON().review_ids as number[];requested.push(...ids);
  return route.fulfill({json:{items:ids.map(id=>({review_id:id,title:`Türkçe başlık ${id}`,review_text:`Türkçe yorum ${id}`})),language:'tr',model:'test'}});
 });
 await page.goto('/reviews');await page.getByLabel('Sayfa başına',{exact:true}).selectOption('100');
 await expect(page.locator('tr[data-review-id]')).toHaveCount(100);
 await page.getByRole('button',{name:'Türkçe yorumları göster',exact:true}).click();
 await expect(page.locator('tr[data-review-id]').first()).toContainText('Türkçe yorum');
 expect(new Set(requested).size).toBeLessThan(100);
 const last=page.locator('tr[data-review-id]').last();await last.scrollIntoViewIfNeeded();
 await last.getByRole('button').click();await expect(page.getByRole('dialog')).toContainText('Türkçe yorum');
 await page.keyboard.press('Escape');
 await page.getByRole('link',{name:'Şikâyet Temaları',exact:true}).click();
 await expect(page.getByRole('button',{name:'Türkçe yorumları göster',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.reload();await expect(page.getByRole('button',{name:'Türkçe yorumları göster',exact:true})).toHaveAttribute('aria-pressed','true');
});
test('business priorities and small samples are visible and filterable',async({page,request})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:'Ürün ve model inceleme öncelikleri'})).toBeVisible();
 await expect(page.getByText('Unknown: 14 yorum',{exact:false})).toContainText('az yorum');
 await page.getByLabel('Departman',{exact:true}).selectOption('Tops');
 const expected=await (await request.get('http://localhost:8000/api/priorities?department=Tops')).json();
 await expect(page.getByTestId('disagreement-count')).toHaveText(`${expected.data.disagreement_count.toLocaleString('tr-TR')} / ${expected.data.compared_count.toLocaleString('tr-TR')} karşılaştırılabilir yorum`);
});
test('human annotation routes are removed',async({request})=>{
 expect((await request.get('/api/evaluation/form')).status()).toBe(404);
 expect((await request.post('/api/evaluation/labels',{data:{}})).status()).toBe(404);
});
