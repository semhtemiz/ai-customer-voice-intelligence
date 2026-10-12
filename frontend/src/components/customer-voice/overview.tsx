"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { IconMessageCircle, IconStar, IconThumbUp, IconAlertTriangle } from "@tabler/icons-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Response, type Overview, type Ratings, type Category } from "@/lib/api";
import { useFilters } from "./shell";
import { PrioritiesPanel } from "./priorities";
import { SentimentPanel } from "./sentiments";
import { localizeLimitation } from "@/lib/locale";
const number = (value: number) => value.toLocaleString("tr-TR");
const metric = (value: number | null, suffix = "") => value === null ? "Veri yok" : (suffix === "%" ? "%" : "") + value.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + (suffix === "%" ? "" : suffix);
type Data = { overview: Response<Overview>; ratings: Response<Ratings>; categories: Response<Category[]> };
export function OverviewScreen() {
  const { filters, setFilters } = useFilters(); const key = JSON.stringify(filters);
  const [state, setState] = useState<{ key: string; data?: Data; error?: string }>();
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ key });
    Promise.all([api.overview(filters, controller.signal), api.ratings(filters, controller.signal), api.categories(filters, controller.signal)])
      .then(([overview, ratings, categories]) => {
        if (new Set([overview.meta.dataset_sha256, ratings.meta.dataset_sha256, categories.meta.dataset_sha256]).size !== 1) throw new Error("Veri seti yükleme sırasında değişti. Yeniden deneyin.");
        if (!controller.signal.aborted) setState({ key, data: { overview, ratings, categories } });
      }).catch(error => { if (!controller.signal.aborted) setState({ key, error: error instanceof Error && error.message !== "Failed to fetch" ? error.message : "Analiz servisine ulaşılamadı. Bağlantınızı kontrol edip yeniden deneyin." }); });
    return () => controller.abort();
  // key is the canonical snapshot of filters; prevents stale responses after edits.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, retry]);
  const current = state?.key === key ? state : undefined;
  const data = current?.data;
  return <>
    <h1 className="sr-only">Overview</h1>
    {current?.error ? <Card role="alert"><CardHeader><CardTitle>Analiz yüklenemedi</CardTitle><CardDescription>{current.error}</CardDescription></CardHeader><CardContent><Button onClick={() => { setState(undefined); setRetry(value => value+1); }}>Yeniden dene</Button></CardContent></Card>
    : !data ? <div role="status" aria-label="Analiz yükleniyor" className="space-y-5"><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[1,2,3,4].map(value => <Skeleton key={value} className="h-36 rounded-xl" />)}</div><Skeleton className="h-80 rounded-xl" /><span className="sr-only">Analiz yükleniyor</span></div>
    : data.overview.data.total_reviews === 0 ? <Card role="status"><CardHeader><CardTitle>Bu filtrelerle eşleşen yorum yok</CardTitle><CardDescription>Başka bir kategori, rating veya arama deneyin.</CardDescription></CardHeader><CardContent><Button onClick={() => setFilters({ department:null,class_name:null,rating:null,sentiment:null,search:null })}>Filtreleri sıfırla</Button></CardContent></Card>
    : <Loaded data={data} />}
  </>;
}
function Loaded({ data }: { data: Data }) {
  const summary = data.overview.data; const meta = data.overview.meta;
  const cards = [
    { id:"total-reviews", label:"Toplam yorum", value:number(summary.total_reviews), note:"Eşleşen tüm yorum kayıtları", icon:IconMessageCircle },
    { id:"average-rating", label:"Ortalama rating", value:metric(summary.avg_rating), note:`5 üzerinden · ${number(summary.valid_rating_count)} geçerli rating`, icon:IconStar },
    { id:"recommendation-rate", label:"Tavsiye oranı", value:metric(summary.recommendation_rate_pct,"%"), note:`${number(summary.valid_recommendation_count)} geçerli yanıt üzerinden`, icon:IconThumbUp },
    { id:"low-rating-share", label:"Düşük rating oranı", value:metric(summary.low_rating_rate_pct,"%"), note:`1–2 yıldız · ${number(summary.valid_rating_count)} geçerli rating`, icon:IconAlertTriangle },
  ];
  return <>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(card => <Card key={card.label} className="gap-3 py-5"><CardHeader className="flex flex-row items-center justify-between px-5"><CardTitle className="text-sm font-medium text-muted-foreground">{card.label}</CardTitle><card.icon className="size-5 text-muted-foreground" aria-hidden="true" /></CardHeader><CardContent className="px-5"><p data-testid={card.id} className="text-3xl font-semibold tracking-tight tabular-nums">{card.value}</p><p className="mt-2 text-xs leading-relaxed text-muted-foreground">{card.note}</p></CardContent></Card>)}</div>
    <div className="grid gap-5 xl:grid-cols-2">
      <Card><CardHeader><CardTitle>Rating dağılımı</CardTitle><CardDescription>Geçerli rating değerlerine göre yorum sayısı · {number(data.ratings.data.invalid_or_missing_rating_count)} eksik veya geçersiz</CardDescription></CardHeader><CardContent><div className="h-64" aria-hidden="true"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.ratings.data.distribution} margin={{ left:0,right:10 }} accessibilityLayer><CartesianGrid vertical={false} stroke="var(--border)" /><XAxis dataKey="rating" tickLine={false} axisLine={false} tick={{ fill:"var(--muted-foreground)",fontSize:12 }} tickFormatter={value => `${value} ★`} /><YAxis width={48} tickLine={false} axisLine={false} tick={{ fill:"var(--muted-foreground)",fontSize:11 }} /><Tooltip contentStyle={{ background:"var(--card)",color:"var(--foreground)",borderColor:"var(--border)",borderRadius:8 }} cursor={{ fill:"var(--muted)" }} /><Bar isAnimationActive={false} dataKey="reviews" name="Yorumlar" fill="var(--chart-1)" radius={[5,5,0,0]} maxBarSize={56} /></BarChart></ResponsiveContainer></div><table className="mt-4 w-full text-xs"><caption className="sr-only">Rating dağılımı değerleri</caption><thead><tr><th className="text-left font-medium text-muted-foreground">Rating</th>{data.ratings.data.distribution.map(row => <th key={row.rating} scope="col" className="font-medium">{row.rating} ★</th>)}</tr></thead><tbody><tr><th scope="row" className="pt-2 text-left font-medium text-muted-foreground">Yorumlar</th>{data.ratings.data.distribution.map(row => <td key={row.rating} className="pt-2 text-center tabular-nums">{number(row.reviews)}</td>)}</tr></tbody></table></CardContent></Card>
      <Card><CardHeader><CardTitle>Kategori memnuniyeti</CardTitle><CardDescription>Departman bazında ortalama rating · yorum sayısına göre sıralı</CardDescription></CardHeader><CardContent><div className="h-64" aria-hidden="true"><ResponsiveContainer width="100%" height="100%"><BarChart layout="vertical" data={data.categories.data} margin={{ left:0,right:15 }} accessibilityLayer><CartesianGrid horizontal={false} stroke="var(--border)" /><XAxis type="number" domain={[0,5]} tickLine={false} axisLine={false} tick={{ fill:"var(--muted-foreground)",fontSize:11 }} /><YAxis type="category" dataKey="department" width={75} tickLine={false} axisLine={false} tick={{ fill:"var(--muted-foreground)",fontSize:11 }} /><Tooltip contentStyle={{ background:"var(--card)",color:"var(--foreground)",borderColor:"var(--border)",borderRadius:8 }} cursor={{ fill:"var(--muted)" }} /><Bar isAnimationActive={false} dataKey="avg_rating" name="Ortalama rating" fill="var(--chart-2)" radius={[0,5,5,0]} maxBarSize={16} /></BarChart></ResponsiveContainer></div><div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">{data.categories.data.map(row => <span key={row.department}>{row.department}: {number(row.reviews)} yorum · {metric(row.avg_rating)} / 5{row.valid_rating_count<30?' · az yorum':''}</span>)}</div><p className="mt-3 text-xs text-muted-foreground">Az yorum: 30’dan az geçerli rating. Küçük grupların ortalaması daha kolay değişir; bu eşik güven ölçümü değildir.</p></CardContent></Card>
    </div>
    <SentimentPanel />
    <PrioritiesPanel />
    <Card className="gap-3"><CardHeader><CardTitle className="text-base">Analiz kapsamı</CardTitle></CardHeader><CardContent><div className="grid gap-4 text-sm sm:grid-cols-3"><div><span className="text-muted-foreground">Metin içeren yorumlar</span><p className="mt-1 font-semibold">{number(meta.text_review_count)} / {number(meta.matched_review_count)}</p></div><div><span className="text-muted-foreground">Sınıflandırılan yorumlar</span><p className="mt-1 font-semibold">{number(meta.sentiment_classified_count)} / {number(meta.text_review_count)}</p></div><div><span className="text-muted-foreground">Sentiment yöntemi</span><p className="mt-1 font-semibold">{meta.sentiment_method || "Henüz çalıştırılmadı"}</p></div></div><details className="mt-4 text-xs text-muted-foreground"><summary className="cursor-pointer font-medium">Yöntem ve sınırlılıklar</summary><ul className="mt-3 space-y-1 leading-relaxed">{meta.limitations.map(note => <li key={note}>• {localizeLimitation(note)}</li>)}</ul></details></CardContent></Card>
  </>;
}
