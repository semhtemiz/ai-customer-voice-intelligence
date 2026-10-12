export type Sentiment = "positive" | "neutral" | "negative" | "unknown";
export type Filters = { department: string | null; class_name: string | null; rating: number | null; sentiment: Sentiment | null; search: string | null };
export const emptyFilters: Filters = { department: null, class_name: null, rating: null, sentiment: null, search: null };
export type Meta = { dataset_sha256: string; filters: Filters; matched_review_count: number; text_review_count: number; sentiment_classified_count: number; sentiment_method: string | null; sentiment_run_id: string | null; topic_run_id: string | null; sentiment_model_id:string|null; sentiment_model_revision:string|null; sentiment_eligible_count:number; sentiment_processed_count:number; topic_method:string|null; taxonomy_version:string|null; limitations: string[] };
export type Response<T> = { data: T; meta: Meta };
export type Overview = { total_reviews: number; valid_rating_count: number; valid_recommendation_count: number; avg_rating: number | null; recommendation_rate_pct: number | null; low_rating_rate_pct: number | null };
export type Ratings = { distribution: { rating: number; reviews: number }[]; valid_rating_count: number; invalid_or_missing_rating_count: number };
export type Category = { department: string; reviews: number; valid_rating_count: number; avg_rating: number | null; low_rating_rate_pct: number | null };
export type Options = { departments: string[]; classes: string[]; ratings: number[]; sentiments: Sentiment[] };
const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");
type Query = Partial<Filters> & { page?: number; page_size?: number };
export function queryString(filters: Query) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value !== null && value !== "") params.set(key, String(value));
  return params.toString();
}
async function get<T>(endpoint: string, filters: Query, signal: AbortSignal, method: "GET" | "POST" = "GET"): Promise<T> {
  let result: globalThis.Response;
  try { result = await fetch(`${base}/api/${endpoint}${method === "GET" ? "?" + queryString(filters) : ""}`, {
    method, ...(method === "POST" ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(filters) } : {}),
    signal: AbortSignal.any([signal, AbortSignal.timeout(12000)]), cache: "no-store",
  }); } catch (error) {
    if (signal.aborted) throw error;
    throw new Error(error instanceof DOMException && error.name === "TimeoutError" ? "Analiz isteği zaman aşımına uğradı. Yeniden deneyin." : "Analiz servisine ulaşılamadı. Bağlantınızı kontrol edip yeniden deneyin.");
  }
  if (!result.ok) throw new Error(result.status === 503 ? "Yorum veritabanı hazır değil. Yeniden deneyin." : `Analiz isteği başarısız oldu (${result.status}).`);
  return result.json();
}
export const api = {
  translations: async (reviewIds:number[],signal:AbortSignal):Promise<Translations> => {
    let result:globalThis.Response;
    try { result=await fetch(`${base}/api/reviews/translations`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({review_ids:reviewIds}),signal:AbortSignal.any([signal,AbortSignal.timeout(65000)]),cache:'no-store'}); }
    catch(error){if(signal.aborted)throw error;throw new Error('Çeviri servisine ulaşılamadı veya istek zaman aşımına uğradı.');}
    if(!result.ok)throw new Error(result.status===503?'Türkçe çeviri servisi hazır değil.':'Türkçe çeviri alınamadı. Yeniden deneyin.');
    return result.json();
  },
  priorities: (filters:Filters,signal:AbortSignal)=>get<Response<Priorities>>("priorities",filters,signal),
  insights: (filters:Filters, signal:AbortSignal) => get<Response<Insights>>("insights",filters,signal,"POST"),
  sentiments: (filters:Filters, signal:AbortSignal) => get<Response<Sentiments>>("sentiments",filters,signal),
  topics: (filters:Filters, signal:AbortSignal) => get<Response<Topics>>("topics",filters,signal),
  topicExamples: (topic:string, filters:Filters, signal:AbortSignal) => get<Response<Review[]>>(`topics/${encodeURIComponent(topic)}/examples`,filters,signal),
  reviews: (filters: Filters, page: number, pageSize: number, signal: AbortSignal) => get<ReviewsPage>("reviews", { ...filters, page, page_size: pageSize }, signal),
  quality: (filters: Filters, signal: AbortSignal) => get<Response<DataQuality>>("data-quality", filters, signal),
  overview: (filters: Filters, signal: AbortSignal) => get<Response<Overview>>("overview", filters, signal),
  ratings: (filters: Filters, signal: AbortSignal) => get<Response<Ratings>>("ratings", filters, signal),
  categories: (filters: Filters, signal: AbortSignal) => get<Response<Category[]>>("categories", filters, signal),
  options: (department: string | null, signal: AbortSignal) => get<Response<Options>>("filter-options", { department }, signal),
};

export type Review = { review_id:number; clothing_id:number|null; title:string|null; review_text:string|null; rating:number|null; recommended_ind:number|null; positive_feedback_count:number|null; division_name:string; department_name:string; class_name:string; sentiment:Sentiment; sentiment_score:number|null; complaint_topics:string[] };
export type ReviewsPage = { items:Review[]; page:number; page_size:number; total:number; total_pages:number; meta:Meta };
export type ReviewTranslation={review_id:number;title:string|null;review_text:string|null};
export type Translations={items:ReviewTranslation[];language:'tr';model:string};
export type FilteredQuality = { review_count:number; missing_text_count:number; missing_title_count:number; invalid_or_missing_rating_count:number; invalid_or_missing_recommendation_count:number; invalid_or_missing_age_count:number; missing_division_count:number; missing_department_count:number; missing_class_count:number };
export type DataQuality = { imported_at:string; import_report:{ file:string; sha256:string; row_count:number; columns:string[]; blank_counts:Record<string,number>; invalid_source_id_count:number; duplicate_source_id_count:number; duplicate_content_excess_count:number; invalid_rating_count:number; invalid_recommendation_count:number; invalid_age_count:number; age_range:number[]|null; kpis:Overview & {text_review_count:number} }; filtered_quality:FilteredQuality };

export type Sentiments={ distribution:{sentiment:Sentiment;reviews:number}[];classified_count:number;text_review_count:number };
export type TopicBin={topic:string;mentions:number;rate_pct:number|null};
export type Topics={ distribution:TopicBin[];candidate_count:number;topic_processed_count:number;topic_failed_count:number;topic_pending_count:number };

export type Evidence={id:string;metric:string;value:number|null;denominator:number|null;review_ids:number[]};
export type InsightStatement={text:string;evidence_ids:string[]};
export type Insights={headline:string;key_findings:InsightStatement[];recommended_actions:InsightStatement[];evidence:Evidence[];limitations:string[];source:'llm'|'rules'|'empty';fallback_reason:'not_configured'|'timeout'|'provider_error'|'invalid_output'|null};

export type Priorities={minimum_product_ratings:number;products:{clothing_id:number;reviews:number;valid_rating_count:number;avg_rating:number|null;low_rating_count:number;low_rating_rate_pct:number;topics:{topic:string;mentions:number}[]}[];disagreement_count:number;compared_count:number;disagreement_examples:Review[]};
