# Frontend

Next.js 16.3.8, React, TypeScript ve Tailwind CSS ile beş ekranlı Customer Voice arayüzü. Recharts grafikler, TanStack Table server-side yorum tablosu, Radix/shadcn UI bileşenleri kullanılır. [Kurulum](../docs/SETUP.md).

Filtreler sayfalar arasında ortak context’te korunur. API verisi checksum/kapsam metadatasıyla sunulur; loading/error/empty/retry durumları ayrı gösterilir. İptal sinyalleri eski filtre yanıtlarının yeni görünümü değiştirmesini önler. API istekleri varsayılan olarak aynı origin `/api/*` üzerinden Docker backend’ine proxy edilir.

TR / EN tercihi localStorage’da tutulur; görünür/açılan yorumlar önce çevrilir, istekler en fazla 5 ID taşır. Çeviri kaynağı EN’den ayrılır, hata halinde İngilizce metin korunur. Arama yalnızca kaynak metinde yapılır. Customer Voice logo/favicon/manifest ikonları aynı SVG çiziminden türetilmiştir.

```bash
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
pnpm test:e2e
```

Browser testleri çalışan backend/frontend ve yerel CSV gerektirir; LLM çağrıları için anahtarları test ortamında boşaltın. TR arayüz testleri kontrollü provider yanıtları kullanır.

OrbynAdmin başlangıç UI kaynağıdır; MIT `LICENSE` korunur. shadcn 4.13.0 CSS yerel `src/styles/shadcn.css`, MIT metni `licenses/shadcn-MIT.md` altında tutulur; CLI/MCP paketi bağımlılıklarda yoktur. [Atıflar](../THIRD_PARTY_NOTICES.md).
