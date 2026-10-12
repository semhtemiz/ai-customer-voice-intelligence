# Güvenlik kapsamı

Bu repository’nin public olması, API’nin internete açık kullanım için hazır olduğu anlamına gelmez. Compose portları yalnızca `127.0.0.1` üzerinde açılır. Uygulamada kullanıcı kimlik doğrulaması veya çok kiracılı veri izolasyonu yoktur. İnternete açılmadan önce authentication/authorization, HTTPS reverse proxy ve ortak istek/harcama limitleri gerekir.

## Uygulanan kontroller

- SQL filtreleri parametre bağlar; LIKE jokerleri literal arama için escape edilir. Sayfalama en fazla 100 yorum, topic kanıtı en fazla 20 kayıt döndürür.
- Seçilen tamamlanmış analysis run ve dataset checksum doğrulanır. API hesaplanan metriklerle kaynak kapsamını ayırır.
- Backend `ALLOWED_HOSTS`, proxy forwarded-host ve açık `CORS_ORIGINS` değerlerini kontrol eder. LLM POST isteklerinde varsa Origin allowlist’e uymalıdır. CORS authentication değildir; Origin’siz CLI istekleri kabul edilir.
- LLM POST endpoint’lerinde yalnızca JSON; 32 KB body sınırı, body alma timeout’u ve bağlantı IP’si başına 30 istek/dakika limiti. `X-Forwarded-For` limit anahtarı olarak kullanılmaz. Limit süreç içidir; frontend proxy üzerinden gelen istemciler ortak kotayı paylaşabilir.
- API anahtarları backend runtime ortamında tutulur. Provider endpoint’leri sabittir; redirect ve otomatik retry yoktur. LLM seçim/çeviri çıktıları doğrulanmadan cache’e veya arayüze alınmaz.
- `nosniff`, frame engelleme ve referrer policy başlıkları; frontend için `frame-ancestors`, `object-src`, `base-uri` kısıtları. Bu CSP, script kaynaklarını tam sınırlayan nonce politikası değildir.
- Docker servisleri tüm Linux capabilities’i düşürür ve `no-new-privileges` kullanır. Frontend non-root kullanıcıyla çalışır. Backend’in kalıcı host bind mount import işlemleri için yazılabilirdir; genel container izolasyonu veya production sandbox garantisi yoktur.

## Yayın içeriği

Public paket allowlist ile hazırlanır. `.env` değerleri, ham CSV/Parquet, DB/yedek, model/çeviri cache’i, kişisel yerel yollar, nested `.git`, geliştirme planları/skill dosyaları ve eski yorum içeren değerlendirme raporları dahil edilmez. Sır taraması bilinen anahtar biçimleri ve credential assignment’larını kontrol eder; tüm olası sırları tespit etme garantisi değildir.

Kaynak ve LLM gösteriminde temel e-posta/telefon maskelemesi vardır. Diğer kişisel bilgiler için kapsamlı PII tespiti yapılmaz. Özel müşteri verisini veya gizli ekran görüntüsünü public repository’ye eklemeyin.

## Kontrol ve bildirim

`python scripts/check_public_security.py`, `pnpm audit --prod` ve `pip-audit -r backend/requirements-runtime.txt` kontrollerini yeniden çalıştırın. Bağımlılık veritabanları zamanla değişir. [İnceleme kaydı](docs/SECURITY_REVIEW.md) mevcut bulguları ve kalan sınırları listeler.

Bir açık veya sızmış anahtar bulursanız public issue’ya anahtar, müşteri metni veya exploit payload koymayın. Repository’de GitHub Private vulnerability reporting etkinleştirildiyse Security → Report a vulnerability kullanın. Bu özellik yayın öncesinde repository sahibi tarafından etkinleştirilmelidir; bu yerel hazırlık onu açmaz. Sızmış anahtarı provider’da iptal etmek gerekir; dosyadan silmek tek başına yeterli değildir.
