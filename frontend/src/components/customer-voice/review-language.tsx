"use client";
import {useCallback,useEffect,useRef,useState,useSyncExternalStore} from 'react';
import {api,type Review,type ReviewTranslation} from '@/lib/api';
import {Button} from '@/components/ui/button';
type Language='en'|'tr';
const preference='customer-voice-review-language';
function subscribe(listener:()=>void){window.addEventListener(preference,listener);window.addEventListener('storage',listener);return()=>{window.removeEventListener(preference,listener);window.removeEventListener('storage',listener);};}
function snapshot():Language{try{return localStorage.getItem(preference)==='tr'?'tr':'en';}catch{return 'en';}}
function setLanguage(value:Language){try{localStorage.setItem(preference,value);}catch{}window.dispatchEvent(new Event(preference));}
export function useReviewLanguage(reviews:Review[],checksum?:string){
 const language=useSyncExternalStore(subscribe,snapshot,()=>'en');
 const [attempt,setAttempt]=useState(0);
 const key=JSON.stringify([checksum,reviews.map(r=>r.review_id)]);
 const [state,setState]=useState<{key:string;items:Record<number,ReviewTranslation>;loading:boolean;requested:number;error?:string}>();
 const prioritize=useRef<(id:number)=>void>(()=>{});
 useEffect(()=>{
  if(language!=='tr'||!reviews.length)return;
  const controller=new AbortController();
  const items:Record<number,ReviewTranslation>={};
  const requested=new Set<number>();const queue:number[]=[];let busy=false;let error:string|undefined;
  const valid=new Set(reviews.filter(r=>r.title||r.review_text).map(r=>r.review_id));
  const publish=()=>setState({key,items:{...items},loading:busy||queue.length>0,requested:requested.size,error});
  async function pump(){
   if(busy||error||controller.signal.aborted)return;
   busy=true;publish();
   try{
    while(queue.length){
     const batch=queue.splice(0,5);
     const result=await api.translations(batch,controller.signal);
     if(controller.signal.aborted)return;
     for(const item of result.items)items[item.review_id]=item;
     publish();
    }
   }catch(cause){if(!controller.signal.aborted)error=cause instanceof Error?cause.message:'Çeviri alınamadı.';}
   finally{busy=false;if(!controller.signal.aborted)publish();}
  }
  function enqueue(id:number,first=false){
   if(!valid.has(id)||items[id])return;
   if(!requested.has(id)){requested.add(id);if(first)queue.unshift(id);else queue.push(id);}
   else if(first&&queue.includes(id)){queue.splice(queue.indexOf(id),1);queue.unshift(id);}
   void pump();
  }
  prioritize.current=id=>enqueue(id,true);
  // Start with the first preview, then translate only reviews approaching the viewport.
  if(reviews[0])enqueue(reviews[0].review_id);
  const observer=new IntersectionObserver(entries=>{
   for(const entry of entries)if(entry.isIntersecting)enqueue(Number((entry.target as HTMLElement).dataset.reviewId));
  },{rootMargin:'120px'});
  document.querySelectorAll('[data-review-id]').forEach(element=>observer.observe(element));
  return()=>{controller.abort();observer.disconnect();prioritize.current=()=>{};};
  // key includes the source checksum and the IDs on this page.
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[language,key,attempt]);
 const current=state?.key===key?state:undefined;
 const translated=useCallback((review:Review)=>language==='tr'?current?.items[review.review_id]:undefined,[language,current]);
 const title=useCallback((review:Review)=>translated(review)?.title??review.title,[translated]);
 const text=useCallback((review:Review)=>translated(review)?.review_text??review.review_text,[translated]);
 const contentLanguage=(review:Review)=>translated(review)?'tr':'en';
 return {language,setLanguage,title,text,contentLanguage,prioritize:(id:number)=>prioritize.current(id),translated,
  completed:Object.keys(current?.items||{}).length,requested:current?.requested||0,
  loading:language==='tr'&&!!current?.loading,error:language==='tr'?current?.error:undefined,retry:()=>setAttempt(value=>value+1)};
}
export function ReviewLanguageControls({view}:{view:ReturnType<typeof useReviewLanguage>}){
 return <div className="space-y-2">
  <div className="flex flex-wrap items-center gap-2"><span className="text-xs font-medium">Yorum dili</span><div role="group" aria-label="Yorum dili" className="flex gap-1">
   <Button size="sm" variant={view.language==='tr'?'default':'outline'} aria-label="Türkçe yorumları göster" aria-pressed={view.language==='tr'} onClick={()=>view.setLanguage('tr')}>TR</Button>
   <Button size="sm" variant={view.language==='en'?'default':'outline'} aria-label="İngilizce yorumları göster" aria-pressed={view.language==='en'} onClick={()=>view.setLanguage('en')}>EN</Button>
  </div></div>
  <p className="text-xs leading-relaxed text-muted-foreground">{view.language==='en'?'İngilizce kaynak yorumlar.':'Makine çevirisi; anlam hataları olabilir. Analiz İngilizce kaynağa dayanır. Bekleyen yorumlar EN gösterilir.'}</p>
  {view.loading&&<p role="status" className="text-xs text-muted-foreground">Türkçe çeviriler hazırlanıyor… {view.completed} / {view.requested}</p>}
  {view.language==='tr'&&!view.loading&&view.completed>0&&<p className="text-xs text-muted-foreground">{view.completed} yorum çevrildi · diğer yorumlar kaydırıldıkça hazırlanır.</p>}
  {view.error&&<div role="alert" className="space-y-2 text-xs"><p>{view.error} Çevrilemeyen yorumlar İngilizce kaynak olarak gösteriliyor.</p><Button size="sm" variant="outline" onClick={view.retry}>Çeviriyi yeniden dene</Button></div>}
 </div>;
}
