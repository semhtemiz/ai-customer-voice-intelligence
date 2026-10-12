"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
export function useResource<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ key:string; data?:T; error?:string }>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ key });
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ key, data });
    }).catch(error => {
      if (!controller.signal.aborted) setState({ key, error: error instanceof Error ? error.message : "Veriler yüklenemedi." });
    });
    return () => controller.abort();
    // key captures all input arguments; load is recreated by the caller.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);
  return { ...(state?.key === key ? state : {}), retry: () => { setState(undefined); setAttempt(value => value+1); } };
}
export function ResourceState({ error, retry }: { error?:string; retry:()=>void }) {
  return error ? <Card role="alert"><CardHeader><CardTitle>Veriler yüklenemedi</CardTitle><CardDescription>{error}</CardDescription></CardHeader><CardContent><Button onClick={retry}>Yeniden dene</Button></CardContent></Card>
    : <div role="status" aria-label="Veriler yükleniyor"><Skeleton className="h-72 rounded-xl" /><span className="sr-only">Veriler yükleniyor</span></div>;
}
