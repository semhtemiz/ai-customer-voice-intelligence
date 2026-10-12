# Public kaynak güvenlik incelemesi

13 Ekim 2026 tarihli yerel kontrol. Public kaynak hazırlığı, internet üzerinden servis yayınlama veya kapsamlı penetration test değildir.

## Bulgu ve düzeltmeler

| Alan | Bulgu | Uygulama |
|---|---|---|
| Next.js | 16.2.10 için npm audit advisory’leri | Next.js / eslint-config-next 16.3.8; [upstream security advisory](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j) |
| Template dependency tree | Yalnızca CSS için shadcn CLI/MCP ağacı yükleniyordu | Kullanılan CSS ve MIT yerel dosyaya alındı; CLI dependency kaldırıldı |
| Transitive paketler | PostCSS, Sharp, browserslist ve brace-expansion bulguları | Düzeltmeli sürümler pnpm overrides/lockfile ile sabitlendi |
| Mutation endpoint’leri | Origin/Host ve body/quota sınırı eksikti | Host + forwarded-host kontrolü, explicit Origin, JSON, 32 KB body, timeout ve 30 POST/dakika/süreç-IP |
| Browser headers | Frame/referrer/content sniffing kısıtları eksikti | Güvenlik başlıkları ve sınırlı CSP eklendi |
| Yayın inventory | Eski rapor/plan/yerel Git geçmişi yanlışlıkla dahil edilebilirdi | Allowlist public snapshot; sır/özel yol taraması ve dosya hash manifest’i |
| Repository otomasyonu | Kaynak/bağımlılık kontrolü yoktu | Read-only token, SHA-pinned checkout/setup, pytest/typecheck/build/public scan/runtime audit ve Dependabot dosyaları |

## Dependency taraması

- İlk `pnpm audit --prod`: 4 critical, 33 high, 39 moderate, 5 low advisory kaydı. Bu sayılar exploitable uygulama zafiyeti sayısı değildir; runtime’da kullanılmayan build/CLI yollarını da içerir.
- Güncel `pnpm audit --prod`: **0 bilinen advisory**; production inventory 219 dependency kaydı.
- Güncel tam frontend audit: **1 high**, yalnızca geliştirme ağacındaki `eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces@3.0.3`.
- Python `pip-audit --no-deps --disable-pip -r backend/requirements.txt`: **49 sabitlenmiş paket**, **0 bilinen advisory**, atlanan paket yok. Bu seçenek pinned listeyi tarar; hash tabanlı supply-chain bütünlüğünü veya container OS paketlerini taramaz.

### Açık geliştirme bulgusu

[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm): deeply nested brace pattern için stack-exhaustion DoS. Kontrolde registry latest `braces` sürümü 3.0.3; audit verisi yayımlanmış patched version göstermedi. Paket production dependency ağacında yoktur. Risk gizlenmedi veya audit ignore ile başarıya çevrilmedi. CI production audit’i başarısız advisory’de durdurur; build/typecheck çalışır. Lint/glob araçlarını güvensiz, dışarıdan sağlanan pattern’lerle çalıştırmayın; upstream düzeltme yayımlandığında geliştirme dependency’si güncellenmelidir.

## Yayın sınırı

Public snapshot ham CSV, müşteri yorum raporları, DB/yedek, anahtarlar, cache/model, `.git`, kişisel dosya yolları ve görev geçmişini içermez. Tek README görseli ana ekrandaki toplulaştırılmış metriklerdir; yorum ekranı veya anahtar görünümü değildir. Secret pattern taraması tüm credential tiplerini yakalama garantisi vermez; GitHub secret scanning/push protection yayın sonrası repository sahibi tarafından açılmalıdır.

Kullanıcı authentication/authorization bulunmaz. Compose yalnızca localhost portlarına bind eder; production internet erişimi için [SECURITY.md](../SECURITY.md) sınırları geçerlidir. Uygulanan CSP script nonce/strict-dynamic politikası değildir; rate limit süreç içinde ve frontend proxy istemcileri için ortak olabilir. Docker image OS-level CVE taraması ve bağımsız penetration test yapılmamıştır.

## Son doğrulama

- Yerel backend: **157 passed**; CSV’li gerçek veri kontrolü dahil.
- Playwright: **40 passed (49,5 s)**; güncel dependency tree ve Docker, LLM anahtarları geçici kapalı. Sonrasında gerçek provider ortamı geri açıldı.
- Docker production build/TypeScript ve iki servis healthcheck geçti. Yedi filtreli API direct/proxy yanıtı eşleşti; kaynak 23.486 kayıt / 22.641 sentiment kapsamı korunur.
- Clean public snapshot: **156 passed, 1 skipped**; ham CSV dağıtılmadığı için yalnızca gerçek CSV kontrolü skip olur. Bu skip beklenen yayın kapsamıdır.
- Bilinen anahtar pattern’lerine ek olarak yerel NVIDIA/OpenAI anahtar değerleri public dosya byte’larıyla karşılaştırıldı; eşleşme yok. Anahtar değerleri çıktılanmadı.
- GitHub Actions ve Dependabot dosyaları hazırlandı; GitHub’a push yapılmadığından hosted CI henüz çalışmadı. Yerel test sonucu hosted CI sonucu olarak sunulmaz.
- Public allowlist: **123 dosya**, tek `screenshots/overview.png`. README local link’leri, ZIP file/hash manifest’i ve nested Git/ham veri/env dışlamaları son paket üzerinde doğrulanır.
