# Docker ile çalıştırma

Docker Desktop açık olmalı. Proje kökünde:

```bash
docker compose up -d --build --wait
docker compose ps
```

Dashboard: http://localhost:3000/reviews · API health: http://localhost:8000/health · Swagger: http://localhost:8000/docs.

Compose frontend ve backend’i birlikte çalıştırır; backend sağlıklı olmadan frontend başlamaz. `restart: unless-stopped` Docker daemon yeniden başladığında servisleri tekrar başlatır. Docker Desktop kapalıysa container’lar da çalışmaz. :3000/:8000 portlarını kullanan eski yerel Next.js/uvicorn süreçleri önce kapatılmalıdır.

## Veri ve anahtarlar

- `dataset/Womens Clothing E-Commerce Reviews.csv` yerelde bulunmalı; `dataset/` salt okunur bind mount’tur. CSV image içine kopyalanmaz. Dataset klasörü yoksa Compose sessizce boş klasör oluşturmaz.
- `backend/data/` kalıcı bind mount’tur. Mevcut `reviews.db`, sentiment/topic sonuçları ve `reviews.translations.db` doğrudan kullanılır; Docker’dan çıkınca dosyalar yerelde kalır.
- Backend başlangıçta atomik/idempotent importer çalıştırır. Aynı checksum’da kayıtlar çoğalmaz ve analiz sonuçları korunur. CSV değişirse importer türetilmiş analizleri geçersizleştirir. CSV yoksa API yanıltıcı boş veriyle başlamaz; container logunda eksik kaynak açıklanır.
- `backend/.env` Compose tarafından yalnızca backend ortamına yüklenir. NVIDIA anahtarı frontend’e, image’a veya kaynak ZIP’e alınmaz. `.env` yoksa KPI ekranları ve rules özeti çalışır; yeni Türkçe çeviri için anahtar gerekir.
- Frontend `/api/*` çağrılarını kendi origin’inden yapar; Next.js bunları Docker ağında `http://backend:8000` adresine yönlendirir. Tarayıcıda Docker servis adı veya ayrı API portuna bağlantı gerekmez. Build sırasında `NEXT_PUBLIC_API_BASE_URL` boş bırakılır; host `.env.local` build context’ine alınmaz.

API image’ında yalnızca import/KPI/keyword topic/remote LLM/çeviri bağımlılıkları vardır. Torch/Transformers ve model ağırlıkları image’a eklenmez. Mevcut yerel demo DB’si sonuçları kalıcı mount’tan sunar. Temiz public checkout’ta DB/model sonucu dağıtılmaz; ilk import sonrası sentiment unknown olur. Yeni dataset’te offline sentiment çalıştırmak için kök README’deki tam Python ortamı ve `classify_reviews` komutları kullanılır; aynı `backend/data/` mount’unda sonuçlar API’ye görünür. Docker’da Apple MPS kullanımı varsayılmaz.

## Yönetim ve sorun giderme

```bash
docker compose logs --tail=60 backend frontend
docker compose restart backend
docker compose stop
docker compose up -d --wait
docker compose down
```

`down` container/network’ü kaldırır; bind mount dosyalarını silmez. Veri yenilemek için DB dosyalarını silmek yerine importer sözleşmesini izleyin. `.env` değeri değişince `docker compose up -d --force-recreate backend` kullanın; yalnızca restart container ortamını yeniden okumaz. Kaynak kod değişince `docker compose up -d --build --wait` gerekir.

`docker compose config --quiet` konfigürasyon doğrulamasıdır. `docker compose config` env değerlerini çıktılayabileceğinden anahtar içeren çıktıyı paylaşmayın. Healthcheck 503 ise backend logunda dataset/import hatasını kontrol edin. Port zaten kullanılıyorsa o porttaki eski host sürecini kapatın. Her iki servis localhost’a bind edilir; bu kurulum yerel demo kapsamındadır.

`python3 scripts/check_docker.py` yedi analitik endpoint’in doğrudan API ve frontend proxy üzerinden aynı filtreli sonucu verdiğini kontrol eder; harici LLM çağrısı yapmaz.

Güvenlik kontrolleri ve kalan sınırlar `docs/SECURITY_REVIEW.md` içinde tutulur.

Şema v2’ye geçiş importer içinde transaction ile yapılır; kaynak kayıtlar, sentiment tahminleri ve geçmiş topic run’ları korunur. Topic v2 kapsamı düşük rating/negative tahmin yanında açık şikâyet ifadesi içerir. Ayrıntılar `docs/SETUP.md` ve `SECURITY.md`.

Container’lar `no-new-privileges` ve `cap_drop: ALL` ile çalışır. Bind mount kullanıcı izinleri yazmayı engelliyorsa host `backend/data/` klasörünün kullanıcı/izinlerini kontrol edin; private veriyi daha geniş izinlerle yayınlamayın. Güvenlik limitleri backend `ALLOWED_HOSTS`/`CORS_ORIGINS` değerleriyle aynı localhost kapsamını kullanır.

3000 portu başka bir uygulamada kullanılıyorsa, o uygulamayı kapatmadan `FRONTEND_PORT=3001 docker compose up -d --build --wait` çalıştırın. Dış frontend portu ve backend CORS origin’i birlikte değişir; container içindeki port 3000 kalır. Kontrol: `FRONTEND_PORT=3001 python scripts/check_docker.py`. Browser testleri için `PLAYWRIGHT_BASE_URL=http://localhost:3001` kullanılır. Yerel tercih kökteki gitignored `.env` içinde `FRONTEND_PORT=3001` olarak saklanabilir; backend anahtarları ayrı `backend/.env` dosyasında kalır.
