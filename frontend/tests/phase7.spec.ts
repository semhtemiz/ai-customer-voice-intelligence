import {test,expect} from 'playwright/test';
import fs from 'node:fs';
test('five screens share the same filter scope and evidence',async({page,request})=>{
 await page.goto('/');await expect(page.getByTestId('total-reviews')).toHaveText('23.486');
 await page.getByLabel('Departman',{exact:true}).selectOption('Tops');await page.getByLabel('Rating',{exact:true}).selectOption('1');
 const query='department=Tops&rating=1';
 const overview=await (await request.get('http://localhost:8000/api/overview?'+query)).json();
 const topics=await (await request.get('http://localhost:8000/api/topics?'+query)).json();
 const total=overview.data.total_reviews.toLocaleString('tr-TR');
 await expect(page.getByTestId('total-reviews')).toHaveText(total);
 for(const [name,target,value] of [['Yorum Gezgini','reviews-total',total],['Veri Kalitesi','filtered-quality-total',total],['Şikâyet Temaları','candidate_count',topics.data.candidate_count.toLocaleString('tr-TR')]]){
  await page.getByRole('link',{name,exact:true}).click();await expect(page.getByTestId(target)).toHaveText(value);
  await expect(page.getByLabel('Departman',{exact:true})).toHaveValue('Tops');await expect(page.getByLabel('Rating',{exact:true})).toHaveValue('1');
 }
 await page.getByRole('link',{name:'AI İçgörüleri',exact:true}).click();await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.locator('#e_total_reviews')).toContainText(total);
 await page.getByRole('link',{name:'Overview',exact:true}).click();await expect(page.getByTestId('total-reviews')).toHaveText(total);
});
for(const [path,endpoint,loading,error,empty] of [
 ['/','overview','Analiz yükleniyor','Analiz yüklenemedi','Bu filtrelerle eşleşen yorum yok'],
 ['/reviews','reviews','Veriler yükleniyor','Veriler yüklenemedi','Bu filtrelerle eşleşen yorum yok'],
 ['/data-quality','data-quality','Veriler yükleniyor','Veriler yüklenemedi','Bu filtrelerle eşleşen kayıt yok.'],
 ['/themes','topics','Veriler yükleniyor','Veriler yüklenemedi','Bu filtrelerle eşleşen şikâyet adayı yok.'],
 ['/insights','insights','Özet üretiliyor','Özet üretilemedi','Bu filtrelerle eşleşen veri yok'],
])test(`final loading/error/empty ${path}`,async({page})=>{
 let fail=true;await page.route(`**/api/${endpoint}*`,async route=>{
  if(fail){await new Promise(resolve=>setTimeout(resolve,400));return route.fulfill({status:503,json:{detail:'Unavailable'}});}
  await route.continue();
 });
 await page.goto(path);if(path==='/insights')await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.getByRole('status',{name:loading}).first()).toBeVisible();await expect(page.getByRole('heading',{name:error})).toBeVisible();
 fail=false;await page.getByRole('button',{name:'Yeniden dene',exact:true}).click();
 await expect(page.getByRole('heading',{name:error})).not.toBeVisible();
 await page.getByLabel('Yorumlarda ara').fill('NoMatchingReviewUniqueString987654321');
 if(path==='/insights')await page.getByRole('button',{name:'Özet üret',exact:true}).click();
 await expect(page.getByText(empty,{exact:path!=='/data-quality'}).first()).toBeVisible();
});
test('final screenshots, tooltip and normal-text contrast',async({page})=>{
 await page.setViewportSize({width:1440,height:1000});fs.mkdirSync('../screenshots',{recursive:true});
 for(const [path,name,ready] of [['/','overview','total-reviews'],['/reviews','reviews','reviews-total'],['/data-quality','data-quality','import-total'],['/themes','themes','topic_processed_count'],['/insights','insights','insight-source']]){
  await page.goto(path);if(path==='/insights')await page.getByRole('button',{name:'Özet üret',exact:true}).click();
  await expect(page.getByTestId(ready)).toBeVisible();
  await page.screenshot({path:`../screenshots/final-${name}.png`});
 }
 await page.goto('/');await expect(page.getByTestId('total-reviews')).toBeVisible();
 await page.locator('.recharts-bar-rectangle').first().hover();await expect(page.locator('.recharts-tooltip-wrapper').first()).toContainText('842');
 for(const dark of [false,true]){
  if(dark)await page.getByRole('button',{name:'Temayı değiştir'}).click();
  const contrast=await page.getByRole('heading',{name:'Ortalama rating',exact:true}).evaluate(el=>{
   function rgb(color:string){const canvas=document.createElement('canvas');canvas.width=canvas.height=1;const c=canvas.getContext('2d')!;c.fillStyle=color;c.fillRect(0,0,1,1);return Array.from(c.getImageData(0,0,1,1).data).slice(0,3);}
   function lum(color:number[]){const v=color.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return .2126*v[0]+.7152*v[1]+.0722*v[2];}
   const card=el.closest('[data-slot=card]')!;const a=lum(rgb(getComputedStyle(el).color));const b=lum(rgb(getComputedStyle(card).backgroundColor));return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
  });expect(contrast).toBeGreaterThanOrEqual(4.5);
 }
});
