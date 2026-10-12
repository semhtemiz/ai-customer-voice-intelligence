"use client";
import {useEffect,useRef,useState} from 'react';
import {api,type Insights,type Response,type InsightStatement} from '@/lib/api';
import {localizeLimitation,evidenceLabel} from '@/lib/locale';
import {useFilters} from './shell';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Card,CardHeader,CardTitle,CardDescription,CardContent} from '@/components/ui/card';
import {Skeleton} from '@/components/ui/skeleton';
const reasons={not_configured:'LLM yapılandırılmadı; hesaplanan kanıtlardan yerel rules özeti üretildi.',timeout:'LLM zaman aşımına uğradı; rules özeti kullanıldı.',provider_error:'LLM servisine ulaşılamadı; rules özeti kullanıldı.',invalid_output:'LLM çıktısı doğrulanamadı; rules özeti kullanıldı.'};
const number=(value:number|null)=>value===null?'Veri yok':value.toLocaleString('tr-TR',{maximumFractionDigits:2});
function Statements({items}:{items:InsightStatement[]}){
 return <ol className="space-y-4">{items.map((item,index)=><li className="rounded-lg border p-4" key={item.text}><p className="text-sm leading-6"><span className="mr-2 font-semibold text-muted-foreground">{index+1}.</span>{item.text}</p><div className="mt-3 flex flex-wrap gap-2 text-xs"><span className="text-muted-foreground">Kanıt:</span>{item.evidence_ids.map(id=><a key={id} href={'#'+id} className="break-all text-primary underline">{evidenceLabel(id.replace(/^e_/,''))}</a>)}</div></li>)}</ol>;
}
export function InsightsScreen(){
 const {filters}=useFilters();const key=JSON.stringify(filters);
 const controller=useRef<AbortController|null>(null);
 const [state,setState]=useState<{key:string;loading?:boolean;data?:Response<Insights>;error?:string}>();
 useEffect(()=>()=>controller.current?.abort(),[key]);
 const current=state?.key===key?state:undefined;
 async function generate(){
  controller.current?.abort();const active=new AbortController();controller.current=active;
  setState({key,loading:true});
  try{const data=await api.insights(filters,active.signal);if(!active.signal.aborted)setState({key,data});}
  catch(error){if(!active.signal.aborted)setState({key,error:error instanceof Error?error.message:'Özet üretilemedi.'});}
 }
 const result=current?.data;
 return <>
 <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground">KANITA DAYALI ÖZET</p><h1 className="text-2xl font-semibold">AI İçgörüleri</h1><p className="mt-2 text-sm text-muted-foreground">Filtreli yorumlara dayalı bulgular ve inceleme önerileri.</p></div><Button disabled={!!current?.loading} onClick={generate}>{current?.loading?'Özet üretiliyor…':result?'Özeti yeniden üret':'Özet üret'}</Button></div>
 {!current&&!state&&<Card><CardHeader><CardTitle>İnceleme önceliklerinizi oluşturun</CardTitle><CardDescription>Aktif filtreler için Özet üret butonunu kullanın.</CardDescription></CardHeader><CardContent><p className="text-sm leading-6 text-muted-foreground">Özet hesaplanan metriklere dayanır. LLM yalnızca kanıta bağlı ifadeleri seçer; kullanılamazsa rules özeti gösterilir.</p></CardContent></Card>}
 {state&&state.key!==key&&<Card role="status"><CardHeader><CardTitle>Filtreler değişti</CardTitle><CardDescription>Önceki özet gizlendi. Güncel kapsam için yeniden Özet üret butonuna basın.</CardDescription></CardHeader></Card>}
 {current?.loading&&<div role="status" aria-label="Özet üretiliyor"><Skeleton className="h-64 rounded-xl"/><span className="sr-only">Özet üretiliyor</span></div>}
 {current?.error&&<Card role="alert"><CardHeader><CardTitle>Özet üretilemedi</CardTitle><CardDescription>{current.error}</CardDescription></CardHeader><CardContent><Button variant="outline" onClick={generate}>Yeniden dene</Button></CardContent></Card>}
 {result&&<>
 <Card><CardHeader><div className="mb-2 flex flex-wrap gap-2"><Badge variant="secondary" data-testid="insight-source">{result.data.source==='llm'?'LLM seçimi':result.data.source==='rules'?'Rules özeti':'Boş veri'}</Badge><Badge variant="outline">{number(result.meta.matched_review_count)} eşleşen yorum</Badge></div><CardTitle>{result.data.headline}</CardTitle><CardDescription>{result.data.fallback_reason?reasons[result.data.fallback_reason]:result.data.source==='llm'?'LLM, hesaplanan kanıtlara bağlı ifadeleri seçti.':'Bu kapsamda bulgu veya öneri üretilemez.'}</CardDescription></CardHeader></Card>
 {result.data.source!=='empty'&&<div className="grid gap-5 xl:grid-cols-2"><Card><CardHeader><CardTitle>Temel bulgular</CardTitle></CardHeader><CardContent><Statements items={result.data.key_findings}/></CardContent></Card><Card><CardHeader><CardTitle>Önerilen incelemeler</CardTitle><CardDescription>Kaynak yorumlarla doğrulanması gereken inceleme adımları.</CardDescription></CardHeader><CardContent>{result.data.recommended_actions.length?<Statements items={result.data.recommended_actions}/>:<p className="text-sm text-muted-foreground">Bu kapsamda desteklenen ek inceleme önerisi bulunmuyor.</p>}</CardContent></Card></div>}
 {result.data.evidence.length>0&&<Card><CardHeader><CardTitle>Kanıt tablosu</CardTitle><CardDescription>Payda her metriğin kapsamını gösterir. Review ID’leri sınırlı kaynak örnekleridir.</CardDescription></CardHeader><CardContent><div className="overflow-x-auto" role="region" aria-label="Kanıt tablosu" tabIndex={0}><table className="w-full text-sm"><caption className="sr-only">Özetin kullandığı hesaplanmış kanıtlar</caption><thead><tr className="border-b text-left text-xs text-muted-foreground">{['Kanıt / metrik','Değer','Payda','Review ID'].map(label=><th key={label} scope="col" className="p-2">{label}</th>)}</tr></thead><tbody>{result.data.evidence.map(evidence=><tr id={evidence.id} key={evidence.id} className="scroll-mt-4 border-b last:border-0"><th scope="row" className="p-2 text-left font-normal">{evidenceLabel(evidence.metric)}</th><td className="p-2 tabular-nums">{number(evidence.value)}</td><td className="p-2 tabular-nums">{number(evidence.denominator)}</td><td className="p-2 text-xs">{evidence.review_ids.length?evidence.review_ids.map(id=>'#'+id).join(', '):'—'}</td></tr>)}</tbody></table></div></CardContent></Card>}
 <Card><CardHeader><CardTitle>Kapsam ve sınırlılıklar</CardTitle><CardDescription>Metin ve analiz kapsamı: {number(result.meta.sentiment_classified_count)} / {number(result.meta.text_review_count)} · yöntem: {result.meta.sentiment_method||'Henüz çalıştırılmadı'}</CardDescription></CardHeader><CardContent><ul className="space-y-2 text-xs leading-relaxed text-muted-foreground">{result.data.limitations.map(note=><li key={note}>• {localizeLimitation(note)}</li>)}</ul><p className="mt-4 break-all font-mono text-xs text-muted-foreground">Dataset SHA-256: {result.meta.dataset_sha256}</p></CardContent></Card>
 </>}
 </>;
}
