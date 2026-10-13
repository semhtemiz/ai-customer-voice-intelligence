# Kurulum ve geliştirme

## Veri

[Kaynak CSV’yi](https://www.kaggle.com/datasets/nicapotato/womens-ecommerce-clothing-reviews) `dataset/Womens Clothing E-Commerce Reviews.csv` yoluna yerleştirin. Başlıksız kaynak indeks kolonunu koruyun. Kaynak dosya, SQLite DB ve model/çeviri cache’leri repository’ye alınmaz. [Profil](../dataset/profile.json) yalnızca toplulaştırılmış doğrulama verisidir.

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up -d --build --wait
```

Frontend http://localhost:3000/; API http://localhost:8000/health. [Ayrıntılar](../DOCKER.md). Temiz kurulum yalnızca CSV’yi import eder; yerel sentiment sonuçları repository’de dağıtılmadığından ilk açılışta tahminler `unknown` olabilir. Aşağıdaki offline işleri aynı `backend/data/` klasöründe çalıştırın.

## Backend ve offline NLP

Python 3.12 kullanın. API/test ortamı için `requirements-runtime.txt`, NLP işleri için `requirements.txt` gerekir.

```bash
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m backend.scripts.import_reviews
python -m backend.scripts.classify_reviews sentiment --batch-size 16
python -m backend.scripts.classify_reviews topics --batch-size 256
```

İlk model indirmesinde ağ erişimi gerekir. Sentiment inference yereldir; yorumlar bu işte harici servise gönderilmez. Model revision sabittir, `trust_remote_code=False`. MPS varsa kullanılabilir; Docker image offline model ağırlıklarını/Torch’u içermez. Sentiment run değişirse bağımlı topic run yeniden üretilir.

Docker kullanmadan API: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`.

## Frontend

Node 24, pnpm 11.25.0:

```bash
cd frontend
pnpm install --frozen-lockfile
cp .env.example .env.local
pnpm dev
```

Production kontrolü: `pnpm build`; tip kontrolü: `pnpm typecheck`; lint: `pnpm lint`. Docker frontend API isteklerini aynı origin üzerinden backend’e proxy eder.

## Opsiyonel LLM

Yalnızca yerel `backend/.env` dosyasında:

```dotenv
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=
NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
NVIDIA_TRANSLATION_MODEL=nvidia/nemotron-3-super-120b-a12b
```

Anahtarı dosyadaki boş değere girin; frontend’e veya repository’ye koymayın. `docker compose up -d --force-recreate backend` ile ortamı yeniden yükleyin. Özet en fazla 20 e-posta/telefon maskelenmiş yorum örneği ve hesaplanan kanıtları; TR çeviri en fazla 5 yorumun maskelenmiş başlık/metnini provider’a gönderir. Maskeler kapsamlı PII tespiti değildir. Yeni verilerde harici veri aktarımı için uygun yetkilendirme gerekir. Hesap kotası ve model erişimi provider’a bağlıdır.

Anahtar olmadan dashboard ve rules özeti çalışır. Provider/model hataları istemciye anahtar veya ham hata metni aktarmaz.

## Kontroller

```bash
python -m pytest backend/tests -q
python scripts/check_public_security.py
python scripts/check_docker.py
```

Tarayıcı testleri yerel dataset ve çalışan Docker servislerini gerektirir. Testte dış LLM çağrısı yapmamak için backend anahtarlarını geçici boşaltın; TR UI testleri mock provider yanıtı kullanır. `frontend` içinde `pnpm exec playwright install chromium` ve `pnpm test:e2e`.

Public kaynak çıktısı: `python scripts/package_release.py`. Çıktı `release/github-public/` ve `release/customer-voice-source.zip`; dosya manifest’i `release/manifest.json`. Çıktı temiz kaynak ağacıdır; çalışma klasöründeki template Git geçmişini, plan/skill dosyalarını veya yerel veriyi kopyalamaz.

`release/github-public/` aktif Git checkout içeriyorsa packager onu değiştirmez; yeni snapshot `release/github-public-export/` altında oluşturulur. ZIP güncel kaynakla yenilenir, mevcut remote/branch/yerel değişiklikler korunur.
