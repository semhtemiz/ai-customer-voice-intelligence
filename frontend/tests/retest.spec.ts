import {test,expect} from 'playwright/test';

test('returning to earlier filters waits for the new source snapshot',async({page})=>{
 let unfiltered=0;
 await page.route('**/api/reviews?**',async route=>{
  const response=await route.fetch();const body=await response.json();
  if(!new URL(route.request().url()).searchParams.has('rating')){
   unfiltered++;
   body.items[0].title=unfiltered===1?'Önceki kaynak sürümü':'Güncel kaynak sürümü';
   if(unfiltered>1){body.meta.dataset_sha256='f'.repeat(64);await new Promise(resolve=>setTimeout(resolve,500));}
  }
  await route.fulfill({response,json:body}).catch(()=>{});
 });
 await page.goto('/reviews');await expect(page.getByText('Önceki kaynak sürümü',{exact:true})).toBeVisible();
 await page.getByLabel('Rating',{exact:true}).selectOption('1');
 await expect(page.getByTestId('reviews-total')).toBeVisible();
 await page.getByRole('button',{name:'Filtreleri temizle',exact:true}).click();
 await expect(page.getByRole('status',{name:'Veriler yükleniyor'})).toBeVisible();
 await expect(page.getByText('Önceki kaynak sürümü',{exact:true})).not.toBeVisible();
 await expect(page.getByText('Güncel kaynak sürümü',{exact:true})).toBeVisible();
});

test('viewport changes switch the sidebar between desktop and mobile',async({page})=>{
 await page.setViewportSize({width:1440,height:1000});await page.goto('/');
 await expect(page.getByRole('link',{name:'Veri seti · Kaggle',exact:true})).toBeVisible();
 await page.setViewportSize({width:375,height:900});
 await expect(page.getByRole('link',{name:'Veri seti · Kaggle',exact:true})).not.toBeVisible();
 await page.getByRole('button',{name:'Menüyü aç/kapat',exact:true}).click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await expect(page.getByRole('link',{name:'Veri seti · Kaggle',exact:true})).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.setViewportSize({width:1440,height:1000});
 await expect(page.getByRole('link',{name:'Veri seti · Kaggle',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
