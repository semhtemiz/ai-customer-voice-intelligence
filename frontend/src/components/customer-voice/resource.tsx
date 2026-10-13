"use client";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
export function useResource<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
  const [attempt, setAttempt] = useState(0);
  const scope = useMemo(() => ({ key, attempt }), [key, attempt]);
  const [state, setState] = useState<{ scope:typeof scope; data?:T; error?:string }>();
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ scope, data });
    }).catch(error => {
      if (!controller.signal.aborted) setState({ scope, error: error instanceof Error ? error.message : "Veriler yüklenemedi." });
    });
    return () => controller.abort();
    // key captures all input arguments; load is recreated by the caller.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);
  return { ...(state?.scope === scope ? state : {}), retry: () => setAttempt(value => value+1) };
}
export function ResourceState({ error, retry }: { error?:string; retry:()=>void }) {
  return error ? <Card role="alert"><CardHeader><CardTitle>Veriler yüklenemedi</CardTitle><CardDescription>{error}</CardDescription></CardHeader><CardContent><Button onClick={retry}>Yeniden dene</Button></CardContent></Card>
    : <div role="status" aria-label="Veriler yükleniyor"><Skeleton className="h-72 rounded-xl" /><span className="sr-only">Veriler yükleniyor</span></div>;
}
