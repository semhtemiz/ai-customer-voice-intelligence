"use client";
import {useReviewLanguage,ReviewLanguageControls} from './review-language';
import {api} from '@/lib/api';
import {topicNames} from '@/lib/locale';
import {useFilters} from './shell';
import {useResource,ResourceState} from './resource';
import {Card,CardHeader,CardTitle,CardDescription,CardContent} from '@/components/ui/card';
const number=(n:number)=>n.toLocaleString('tr-TR');
export function PrioritiesPanel(){
 const {filters}=useFilters();const resource=useResource(JSON.stringify(filters),signal=>api.priorities(filters,signal));
 const data=resource.data?.data;
 const view=useReviewLanguage(data?.disagreement_examples||[],resource.data?.meta.dataset_sha256);
 return <Card><CardHeader><CardTitle>Ürün ve model inceleme öncelikleri</CardTitle><CardDescription>Düşük rating ürünleri ve rating–sentiment yön farkları.</CardDescription></CardHeader><CardContent className="space-y-6">
 {!data?<ResourceState error={resource.error} retry={resource.retry}/>:<>
 <div><h3 className="mb-2 text-sm font-semibold">Tekrar eden düşük rating</h3><p className="mb-3 text-xs text-muted-foreground">En az {data.minimum_product_ratings} geçerli rating içeren ürünler arasında düşük rating oranına göre ilk 10. Payda, ürünün bu filtrelerdeki geçerli rating sayısıdır.</p>
 {!data.products.length?<p className="text-sm text-muted-foreground">Bu kapsamda eşiği karşılayan düşük rating ürünü yok.</p>:<div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Ürün inceleme öncelikleri</caption><thead><tr className="border-b text-left">{['Ürün ID','Geçerli rating','Düşük rating','Oran','Gözlenen topic'].map(label=><th key={label} className="p-2" scope="col">{label}</th>)}</tr></thead><tbody>{data.products.map(p=><tr key={p.clothing_id} className="border-b"><th scope="row" className="p-2 text-left">#{p.clothing_id}</th><td className="p-2">{number(p.valid_rating_count)}{p.valid_rating_count<30?' · az yorum':''}</td><td className="p-2">{number(p.low_rating_count)}</td><td className="p-2">%{number(p.low_rating_rate_pct)}</td><td className="p-2 text-xs">{p.topics.length?p.topics.map(t=>`${topicNames[t.topic]||t.topic}: ${number(t.mentions)}`).join(' · '):'Topic kanıtı yok'}</td></tr>)}</tbody></table></div>}</div>
 <div><h3 className="text-sm font-semibold">Rating–sentiment yön farkı</h3><p className="mt-2 text-sm" data-testid="disagreement-count">{number(data.disagreement_count)} / {number(data.compared_count)} karşılaştırılabilir yorum</p><p className="mt-2 text-xs leading-relaxed text-muted-foreground">1–2 rating + positive veya 4–5 rating + negative tahmin. Yön farkı tek başına model hatası değildir. ID sırasıyla ilk 20 yoruma kadar gösterilir.</p>
 <ReviewLanguageControls view={view}/><div className="mt-3 space-y-2">{data.disagreement_examples.map(r=><details onToggle={event=>{if(event.currentTarget.open)view.prioritize(r.review_id);}} key={r.review_id} className="rounded-md border p-3"><summary className="cursor-pointer text-sm">Yorum #{r.review_id} · Ürün #{r.clothing_id??'—'} · Rating {r.rating} · {r.sentiment}</summary><p data-review-id={r.review_id} lang={view.contentLanguage(r)} className="mt-3 whitespace-pre-wrap break-words text-sm leading-6">{view.language==='tr'&&!view.translated(r)?'EN · kaynak: ':''}{view.text(r)||'Yorum metni yok'}</p></details>)}</div></div>
 </>}
 </CardContent></Card>;
}
