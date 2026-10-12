# Backend

FastAPI/SQLite API, atomik CSV import ve sürümlü NLP/topic işleri. [Kurulum](../docs/SETUP.md), [güvenlik kapsamı](../SECURITY.md).

## API

| Endpoint | Kapsam |
|---|---|
| `GET /health` | Import ve schema hazır olma durumu |
| `GET /api/overview`, `/api/ratings`, `/api/categories` | Filtreli metrikler ve dağılımlar |
| `GET /api/reviews` | Kararlı ID sırası; sayfa boyutu en fazla 100 |
| `GET /api/sentiments` | Seçili tamamlanmış model run dağılımı |
| `GET /api/topics`, `/api/topics/{topic}/examples` | Çoklu topic; en fazla 20 kaynak örnek |
| `GET /api/priorities` | Ürün düşük rating öncelikleri ve rating–sentiment yön farkları |
| `GET /api/data-quality`, `/api/filter-options` | Import/filtreli kalite ve seçenekler |
| `POST /api/insights` | Backend kanıt kataloğundan doğrulanmış seçim/rules özeti |
| `POST /api/reviews/translations` | En fazla 5 benzersiz kaynak ID için display-only çeviri |

Ortak filtreler: department, class_name, rating, sentiment, search. Query parametreleri bağlanır; bilinmeyen/uygunsuz filtre 422, bilinmeyen topic/ID 404, DB hazır değilse 503. Sıfır paydada ortalama/oran null. Genel import raporu aktif filtrelerden ayrı kalır.

API yalnızca dataset checksum’ıyla uyumlu tamamlanmış seçili sentiment/topic run’ını kullanır. Sentiment değişince bağımlı topic seçimi geçersizleşir. Schema v1 → v2 import içinde atomik taşınır; kaynak ID, ham metin ve geçmiş run’lar korunur. CSV checksum değişince eski türetilmiş analizler kaldırılır.

Topic v2 adayları: metin + düşük rating, negative sentiment veya açık şikâyet ifadesi. Çoklu etiketler bridge tablosunda tutulur; topic paydası işlenmiş aday sayısıdır. Anahtar kelime yöntemi gerçek etiket doğruluğu değildir.

## Provider ve cache

Özet provider’ı backend’de onaylı bulgu/öneri ID’lerini seçer. JSON şeması, unique ID, scope ve kanıt referansları doğrulanır; unsupported/timeout/error durumunda rules fallback. NVIDIA’ya en fazla 8 bulgu/5 öneri seçeneği ve 20 maskelenmiş örnek sunulur. API anahtarı istemciye aktarılmaz.

Çeviri yalnızca backend’den sorgulanan başlık/metni kullanır; arbitrary client metni kabul edilmez. Ayrı SQLite cache anahtarı checksum/model/prompt sürümü/kaynak hash’ine bağlıdır. Ölçü yer tutucuları ve null/ID alanları doğrulanır; bozuk batch cache’e alınmaz. Yapısal kontrol tüm anlam hatalarını yakalamaz. Kaynak DB ve NLP girdisi İngilizce kalır.

Offline model indirmesinde immutable revision ve `trust_remote_code=False` kullanılır. Runtime Docker image model ağırlıkları/Torch’u içermez. Anahtarlar yalnızca `backend/.env`; örnek ayarlar `.env.example`. Güvenlik limitleri [SECURITY.md](../SECURITY.md) içinde.
