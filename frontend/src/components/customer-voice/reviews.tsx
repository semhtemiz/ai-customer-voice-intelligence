"use client";
import { useMemo, useRef, useState } from "react";
import { useReactTable, getCoreRowModel, flexRender, type ColumnDef } from "@tanstack/react-table";
import { api, emptyFilters, type Review } from "@/lib/api";
import { useFilters } from "./shell";
import { useResource, ResourceState } from "./resource";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import {useReviewLanguage,ReviewLanguageControls} from "./review-language";
const number = (value:number) => value.toLocaleString("tr-TR");
const recommendation = (value:number|null) => value === null ? "Bilinmiyor" : value === 1 ? "Evet" : "Hayır";
export function ReviewsScreen() {
  const { filters, setFilters } = useFilters();
  const filtersKey = JSON.stringify(filters);
  const [pagination, setPagination] = useState({ key:filtersKey, page:1, size:20 });
  const page = pagination.key === filtersKey ? pagination.page : 1;
  const size = pagination.size;
  const key = JSON.stringify([filtersKey,page,size]);
  const resource = useResource(key, signal => api.reviews(filters,page,size,signal));
  const view = useReviewLanguage(resource.data?.items || [],resource.data?.meta.dataset_sha256);
  const returnFocus = useRef<HTMLButtonElement | null>(null);
  const returnFocusId = useRef<number | null>(null);
  const [selection,setSelection] = useState<{ key:string; review:Review } | null>(null);
  const selected = selection?.key === key ? selection.review : null;
  const columns = useMemo<ColumnDef<Review>[]>(() => [
    { accessorKey:"review_id", header:"ID", cell: info => <span className="tabular-nums text-muted-foreground">#{String(info.getValue())}</span> },
    { accessorKey:"title", header:"Yorum", cell: ({ row }) => <button className="block w-full min-w-48 max-w-sm text-left focus-visible:outline-2 focus-visible:outline-primary" aria-label={`Yorum #${row.original.review_id} ayrıntısını aç`} onClick={event => { returnFocus.current = event.currentTarget; returnFocusId.current = row.original.review_id; setSelection({ key,review:row.original }); view.prioritize(row.original.review_id); }}>{view.language==='tr'&&!view.translated(row.original)&&<span className="block text-xs text-muted-foreground">EN · kaynak</span>}<span lang={view.contentLanguage(row.original)} className="block truncate font-medium">{view.title(row.original)?.trim() || "Başlıksız yorum"}</span><span lang={view.contentLanguage(row.original)} className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{view.text(row.original)?.trim() || "Yorum metni yok"}</span></button> },
    { accessorKey:"department_name", header:"Departman", cell: ({ row }) => <div>{row.original.department_name}<span className="mt-1 block text-xs text-muted-foreground">{row.original.class_name}</span></div> },
    { accessorKey:"rating", header:"Rating", cell: ({ row }) => row.original.rating === null ? "Veri yok" : `${row.original.rating} ★` },
    { accessorKey:"recommended_ind", header:"Tavsiye", cell: ({ row }) => recommendation(row.original.recommended_ind) },
    { accessorKey:"sentiment", header:"Sentiment", cell: ({ row }) => <Badge variant="secondary">{row.original.sentiment}</Badge> },
    { id:"topics", header:"Topic", cell: ({ row }) => row.original.complaint_topics.length ? <div className="flex flex-wrap gap-1">{row.original.complaint_topics.map(topic => <Badge variant="outline" key={topic}>{topic}</Badge>)}</div> : <span className="text-xs text-muted-foreground">Etiket yok</span> },
  ], [key,view.title,view.text]);
  const table = useReactTable({ data:resource.data?.items || [], columns, getCoreRowModel:getCoreRowModel(), manualPagination:true, state:{ pagination:{pageIndex:page-1,pageSize:size} }, rowCount:resource.data?.total || 0, getRowId:row => String(row.review_id) });
  const navigate = (next:number) => setPagination({ key:filtersKey,page:next,size });
  return <>
    <div><p className="mb-2 text-xs font-semibold tracking-widest text-muted-foreground">YORUM KANITLARI</p><h1 className="text-2xl font-semibold">Yorum Gezgini</h1><p className="mt-2 text-sm text-muted-foreground">Kaynak yorumları, rating ve sentiment sonuçlarıyla inceleyin.</p></div>
    {!resource.data ? <ResourceState error={resource.error} retry={resource.retry} /> : <Card>
      <CardHeader><CardTitle>Eşleşen yorumlar</CardTitle><ReviewLanguageControls view={view}/><CardDescription><span data-testid="reviews-total">{number(resource.data.total)}</span> kayıt · sentiment yöntemi: {resource.data.meta.sentiment_method || "Henüz çalıştırılmadı"}</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        {resource.data.items.length ? <div className="overflow-x-auto rounded-md border" role="region" aria-label="Yorum tablosu" tabIndex={0}><table className="w-full text-sm"><caption className="sr-only">Filtrelenmiş müşteri yorumları; ayrıntı için yorum başlığını açın.</caption><thead className="bg-muted/60">{table.getHeaderGroups().map(group => <tr key={group.id}>{group.headers.map(header => <th key={header.id} scope="col" className="whitespace-nowrap p-3 text-left text-xs font-medium text-muted-foreground">{flexRender(header.column.columnDef.header,header.getContext())}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map(row => <tr key={row.id} data-review-id={row.original.review_id} className="border-t align-top hover:bg-muted/25">{row.getVisibleCells().map(cell => <td key={cell.id} className="p-3">{flexRender(cell.column.columnDef.cell,cell.getContext())}</td>)}</tr>)}</tbody></table></div>
          : <div role="status" className="rounded-lg border border-dashed p-8 text-center"><h2 className="font-semibold">{resource.data.total === 0 ? "Bu filtrelerle eşleşen yorum yok" : "Bu sayfada yorum yok"}</h2><p className="mt-2 text-sm text-muted-foreground">Filtreleri sıfırlayın veya ilk sayfaya dönün.</p><Button variant="outline" className="mt-4" onClick={() => { setFilters({ ...emptyFilters }); navigate(1); }}>Filtreleri sıfırla</Button></div>}
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm"><label className="flex items-center gap-2">Sayfa başına<select aria-label="Sayfa başına" className="h-9 rounded-md border bg-background px-2" value={size} onChange={event => setPagination({key:filtersKey,page:1,size:Number(event.target.value)})}>{[10,20,50,100].map(value => <option key={value}>{value}</option>)}</select></label><span data-testid="page-info">Sayfa {resource.data.total_pages ? page : 0} / {number(resource.data.total_pages)}</span><div className="flex gap-2"><Button variant="outline" disabled={page <= 1} onClick={() => navigate(1)}>İlk sayfa</Button><Button variant="outline" disabled={page <= 1} onClick={() => navigate(page-1)}>Önceki</Button><Button variant="outline" disabled={page >= resource.data.total_pages} onClick={() => navigate(page+1)}>Sonraki</Button></div></div>
        <p className="text-xs leading-relaxed text-muted-foreground">ID sırasıyla gösterilir. E-posta/telefon için temel maskeleme uygulanır; tüm kişisel bilgileri kapsamaz. unknown, sentiment sonucu olmayan kayıttır.</p>
      </CardContent>
    </Card>}
    <Sheet open={!!selected} onOpenChange={open => { if (!open) setSelection(null); }}><SheetContent onCloseAutoFocus={event => { event.preventDefault(); const trigger=returnFocus.current?.isConnected?returnFocus.current:document.querySelector<HTMLButtonElement>(`tr[data-review-id="${returnFocusId.current}"] button`); trigger?.focus(); }} className="w-full overflow-y-auto sm:max-w-xl">
      <SheetHeader><SheetTitle>Yorum #{selected?.review_id}</SheetTitle><SheetDescription>Kaynak metin ve analiz sonuçları.</SheetDescription></SheetHeader>
      {selected && <div className="space-y-6 p-4 pt-0"><ReviewLanguageControls view={view}/><div>{view.language==='tr'&&!view.translated(selected)&&<p className="mb-2 text-xs text-muted-foreground">EN · kaynak</p>}<h2 lang={view.contentLanguage(selected)} className="font-semibold">{view.title(selected)?.trim() || "Başlıksız yorum"}</h2><p lang={view.contentLanguage(selected)} className="mt-3 whitespace-pre-wrap break-words text-sm leading-7">{view.text(selected)?.trim() || "Yorum metni bulunmuyor."}</p></div><dl className="grid grid-cols-2 gap-4 text-sm">{[["Ürün ID",selected.clothing_id ?? "Veri yok"],["Rating",selected.rating === null ? "Veri yok" : `${selected.rating} / 5`],["Tavsiye",recommendation(selected.recommended_ind)],["Olumlu geri bildirim",selected.positive_feedback_count ?? "Veri yok"],["Departman",selected.department_name],["Ürün sınıfı",selected.class_name]].map(([label,value]) => <div key={label}><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>)}</dl><div><h3 className="mb-2 text-sm font-semibold">Sentiment tahmini</h3><Badge variant="secondary">{selected.sentiment}</Badge><p className="mt-2 text-xs text-muted-foreground">{resource.data?.meta.sentiment_method || "Analiz henüz çalıştırılmadı"}{selected.sentiment_score === null ? " · Model skoru yok" : ` · Model skoru: ${selected.sentiment_score.toLocaleString("tr-TR")}`}. Model skoru doğruluk oranı değildir.</p></div><div><h3 className="mb-2 text-sm font-semibold">Topic etiketleri</h3>{selected.complaint_topics.length ? <div className="flex flex-wrap gap-2">{selected.complaint_topics.map(topic => <Badge key={topic} variant="outline">{topic}</Badge>)}</div> : <p className="text-sm text-muted-foreground">{resource.data?.meta.topic_run_id ? "Bu yorumun topic etiketi yok; henüz işlenmemiş olabilir." : "Topic analizi henüz çalıştırılmadı."}</p>}</div></div>}
    </SheetContent></Sheet>
  </>;
}
