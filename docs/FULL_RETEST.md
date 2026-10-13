# Tüm proje kontrolü — 13 Ekim 2026

## Sonuç

Yerel backend **157 test geçti**. Beş ekranı kapsayan mevcut **40 browser testi (50,2 s)** ve iki yeni regresyon testi (**2 geçti; 3,4 s**) başarılı. Lint ve TypeScript kontrolü temiz; Docker production build ve frontend/backend healthcheck başarılı. Bu işlevsel kontrol, model doğruluğu veya insan çeviri kalite benchmark değildir.

## Bulunan ve giderilen sorunlar

- Docker servisleri durmuştu. 3000 portu başka bir yerel uygulama tarafından kullanılıyordu; o uygulamaya dokunulmadan Customer Voice 3001’de başlatıldı. `FRONTEND_PORT` varsayılanı 3000; dış frontend portu, backend CORS origin’i ve QA script’leri birlikte değiştirilebilir.
- Lint’te effect içinde dört gereksiz state güncellemesi ve üç uyarı vardı. API yüklemeleri her filtre/retry turunu ayrı scope ile izler; eski yanıtlar iptal edilir, önceki scope tekrar kullanılmış filtrede güncel cevap gibi sunulmaz. Tema hydration’ı ve mobil breakpoint, `useSyncExternalStore` üzerinden takip edilir.
- Review columns güncel dil/view callback’lerini doğrudan kullanır; eksik useMemo dependency kaldırıldı. TanStack mutable API için React Compiler kapalı olduğundan yalnızca ilgili lint satırı belgelenmiştir; lint kuralları genel olarak kapatılmamıştır.
- CI’ye lint eklendi; önceki filter scope’a dönme ve desktop/mobile geçişleri için iki browser regresyonu eklendi.
- Public packager, mevcut `release/github-public/.git` checkout’unu taşımadan export üretir; Git metadata/yerel branch korunur.

## Kapsam

| Kontrol | Gözlenen sonuç |
|---|---|
| CSV checksum/kayıt/KPI | Orijinal profil ile eşit; 23.486 kayıt |
| Sentiment kapsamı | 22.641 / 22.641; boş metinli kayıtlar unknown |
| Topic kapsamı | 9.180 / 9.180; 0 pending/failed |
| Yedi analitik API | Aynı filtreyle direct backend/proxy yanıtları eşit |
| Canlı API güvenlik sınırları | Geçersiz Origin 403, büyük body 413, bilinmeyen review ID 404 |
| Offline gerçek NLP | CPU’da 3 positive/3 neutral/3 negative örneğin 9/9 kayıtlı etiketi yeniden üretildi; yaklaşık 4,65 s |
| Gerçek NVIDIA özet | HTTP 200, source=llm, 7 bulgu/5 öneri; kanıt referansları geçerli; 5,53 s |
| Çeviri cache | HTTP 200; üç kaynak ID; 0,03 s |
| Gerçek Super çeviri | HTTP 200; tek maskelenmiş yorum ID 21; 2,48 s |
| UI | Overview, Reviews, Themes, Insights, Quality; filtre, pagination, eski yanıt, empty/error/retry/loading, TR/EN/cache/retry, modal focus, 1440/768/375 px, light/dark |
| Güvenlik taraması | Frontend production 0 advisory; 49 Python paketinde 0 advisory, atlanan yok |
| Tam frontend audit | Önceki braces geliştirme bağımlılığı için 1 high devam ediyor; production ağacında yok |
| Public kaynak taraması | Sır/private path eşleşmesi yok; ham CSV/DB/cache/Git metadata publish inventory dışında |
| GitHub main | Önceki yayın CI başarılı; PR/CI/admin koruması açık, force push/silme kapalı |

Browser regresyonları sırasında NVIDIA/OpenAI anahtarları yalnızca container test ortamında boşaltıldı; UI translation yanıtları test doubles kullanır. Sonrasında gerçek yerel provider ortamı geri açıldı. Canlı kontrolde yalnızca önceden onaylanan sınırlı maskelenmiş örnekler/hesaplanan kanıtlar gönderildi. API anahtarları rapora veya source’a yazılmadı.

NLP yeniden üretiminde classification için kullanılmayan iki pooler weight’i için loader uyarısı görüldü; classification çıktıları 9/9 kayıtlı etiketle eşleşti. Bu eşleşme gerçek sentiment doğruluğu değildir. Tweet domain farkı, keyword baseline/örtük bağlam hataları ve Türkçe çeviri anlam hataları devam edebilir.

## Çalıştırılan kontroller

- `python -m pytest backend/tests -q`
- `pnpm lint`, `pnpm typecheck`, Docker production `pnpm build`
- `PLAYWRIGHT_BASE_URL=http://localhost:3001 pnpm test:e2e` (mevcut 40 test ve yeni 2 regresyon ayrı çalıştırıldı)
- `FRONTEND_PORT=3001 python scripts/check_docker.py`
- `pnpm audit --prod`, tam `pnpm audit`; pinned `requirements.txt` için pip-audit
- `python scripts/check_public_security.py`; CSV profile karşılaştırması, gerçek offline NLP ve canlı provider smoke kontrolleri

Yerel demo bu kontrolde http://localhost:3001/ üzerinde çalışır. Varsayılan temiz kurulum portu 3000’dır. Port değişikliği internet hosting/auth eklemez; [güvenlik sınırları](../SECURITY.md) ve [açık geliştirme advisory’si](SECURITY_REVIEW.md) geçerlidir.
