"use client";
import { api } from "@/lib/api";
import { useFilters } from "./shell";
import { useResource, ResourceState } from "./resource";
import { Card,CardHeader,CardTitle,CardDescription,CardContent } from "@/components/ui/card";
const number=(value:number)=>value.toLocaleString('tr-TR');
export function SentimentPanel() {
 const {filters}=useFilters();const resource=useResource(JSON.stringify(filters),signal=>api.sentiments(filters,signal));
 if(!resource.data)return <ResourceState error={resource.error} retry={resource.retry}/>;
 const {data,meta}=resource.data;
 return <Card><CardHeader><CardTitle>{meta.sentiment_method==='rating_heuristic'?'Sentiment dağılımı · rating heuristic':meta.sentiment_method?'Sentiment dağılımı · model tahmini':'Sentiment dağılımı'}</CardTitle><CardDescription>{meta.sentiment_method==='rating_heuristic'?'Metinli yorumların rating değerinden türetilir; NLP tahmini değildir.':meta.sentiment_method?'Metin üzerinden tahmin edilir; rating model girdisi değildir.':'Henüz uyumlu sentiment sonucu bulunmuyor.'} unknown, sınıflandırılmamış kayıtları gösterir.</CardDescription></CardHeader><CardContent className="space-y-4"><div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{data.distribution.map(bin=><div key={bin.sentiment} className="rounded-lg border p-3"><p className="text-xs text-muted-foreground">{bin.sentiment}</p><p className="mt-2 text-xl font-semibold tabular-nums" data-testid={`sentiment-${bin.sentiment}`}>{number(bin.reviews)}</p></div>)}</div><p className="text-sm" data-testid="sentiment-coverage">Filtreli metin kapsamı: {number(data.classified_count)} / {number(data.text_review_count)}</p><details className="text-xs text-muted-foreground"><summary className="cursor-pointer font-medium">Analiz yöntemi</summary><p className="mt-3">Run kapsamı: {number(meta.sentiment_processed_count)} / {number(meta.sentiment_eligible_count)} uygun yorum · yöntem: {meta.sentiment_method || 'Henüz çalıştırılmadı'}</p>{meta.sentiment_model_id&&<p className="break-all text-xs text-muted-foreground">Model: {meta.sentiment_model_id}<br/>Revision: {meta.sentiment_model_revision}</p>}</details></CardContent></Card>;
}
