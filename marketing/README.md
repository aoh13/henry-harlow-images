# Henry Harlow — Meta ve Pinterest reklam altyapısı

Bu klasör reklamların dört parçasını kurar:

| Parça | Ne yapar | Nerede |
|---|---|---|
| **İzleme** (pixel + Conversions API) | Ziyaret, ürün görüntüleme, sepet, ödeme ve satın alma olaylarını tarayıcıdan ve sunucudan gönderir | Shopify'ın resmi **Facebook & Instagram** ve **Pinterest** uygulamaları |
| **Numune olayı** | Numune içeren siparişi ayrı bir olay olarak gönderir (Meta: `SampleOrder`, Pinterest: `lead`) | `sample-order-pixel.js` → Shopify Customer events |
| **Ürün kataloğu** | Fiyat, stok ve görselleri canlı mağazadan alır, malzeme/desen/renk/fiyat etiketlerini ekler, her sabah yeniler | `build_feeds.py` → `feeds/meta.csv`, `feeds/pinterest.csv` |
| **Reklam görselleri** | 15 konsept × 4 boyut = 60 hazır görsel ve platform metinleri | `build_creatives.py` → `creatives/` |

İzleme için uygulamaları kullanıyoruz, çünkü Shopify'ın ödeme sayfasına kendi kodumuzu koyamıyoruz ve sunucu tarafı olayları (CAPI) uygulamalar kendisi kuruyor. Kataloğu ise kendimiz üretiyoruz. Uygulamaların senkronladığı katalogda reklamları bölmek için gereken desen, renk, fiyat kademesi ve iç/dış mekân bilgisi yok.

---

## 1. Tek seferlik kurulum

### Ön koşul
- Mağaza şifresiz yayında olmalı. Feed `/products.json` adresinden okunuyor ve şifreli mağazada bu adres kapalı.
- GitHub'da **Settings → Secrets and variables → Actions → Variables** altına `STORE_URL` ekle (mağazanın açık adresi, ör. `https://www.ornek-magaza.com`). Ardından **Actions → Ad catalog feeds → Run workflow** ile ilk feed'i üret.

Feed adresleri (platformlara bunlar verilecek):
```
https://raw.githubusercontent.com/aoh13/henry-harlow-images/main/feeds/meta.csv
https://raw.githubusercontent.com/aoh13/henry-harlow-images/main/feeds/pinterest.csv
```

### Meta
1. **Business Manager** ve bir **reklam hesabı** aç (USD, saat dilimi: mağazanınki).
2. Shopify'a **Facebook & Instagram** uygulamasını kur, Business Manager'a bağla. *Customer data sharing* ayarını **Maximum** yap; bu ayar Conversions API'yi açar.
3. **Business Settings → Brand safety → Domains** altında mağaza alan adını doğrula.
4. **Commerce Manager → Katalog oluştur → E-ticaret → "Henry Harlow – Ads"** → *Data sources → Data feed → Scheduled feed* → `meta.csv` adresi, **günlük, 07:00 (ET)**, para birimi USD.
5. **Events Manager**'da pikseli bu kataloğa bağla (*Catalog → Settings → Event sources*).
6. **Events Manager → Custom conversions → Create**: olay `SampleOrder`, ad "Numune siparişi".
7. 1–2 gün sonra **Catalog → Diagnostics** ekranında piksel ile katalog arasındaki *ID eşleşme oranına* bak. Feed ID olarak Shopify varyant ID'si kullanıyor; Shopify uygulamasının pikseli de normalde varyant ID gönderir. Oran düşükse `feed_config.json` içindeki `id_format.meta` değerini değiştir (ör. `shopify_US_{product_id}_{variant_id}`) ve workflow'u yeniden çalıştır.

> Uygulama Meta'da kendi kataloğunu da oluşturur. Onu silme ama reklamlarda **"Henry Harlow – Ads"** kataloğunu seç, çünkü etiketler yalnızca bunda var.

### Pinterest
1. Pinterest **Business** hesabı aç, reklam hesabı oluştur (USD, ABD).
2. Shopify'a **Pinterest** uygulamasını kur. Uygulama alan adını doğrular ve Pinterest Tag ile Conversions API'yi kurar.
3. **Ads → Catalogs → Data sources → Add data source** → `pinterest.csv` adresi, CSV, USD, en-US, **günlük** güncelleme.
4. Uygulama da bir katalog kaynağı eklediyse **yalnızca birini** bırak. Aynı ürünün iki kopyası sorun çıkarır. Bizim feed'i tut.
5. 1–2 gün sonra **Conversions → Tag health / Catalog** ekranında tag eşleşmesini kontrol et. Gerekirse `id_format.pinterest` değerini değiştir.

### Numune olayı
1. Shopify **Settings → Customer events → Add custom pixel** → ad: "Sample orders".
2. `sample-order-pixel.js` içeriğini yapıştır. En üstteki `META_PIXEL_ID` ve `PINTEREST_TAG_ID` alanlarını doldur.
3. Permission: **Required → Marketing**. Data sale: **qualifies as data sale**. Save → Connect.
4. Numune varyantının adında "sample" geçmiyorsa `SAMPLE_PATTERN` değerini ve `feed_config.json` içindeki `sample_variant_pattern` değerini birlikte değiştir.
5. Test: bir numune siparişi ver, ardından Meta **Events Manager → Test events** ve Pinterest **Tag event history** ekranlarına bak.

---

## 2. Katalog alanları

Feed her **numune olmayan** varyant için bir satır içerir. Numuneler feed'e alınmaz; böylece reklamda $5'lık numune yerine kutu fiyatı görünür.

| Alan | Değer | Kaynak |
|---|---|---|
| `id` | Shopify varyant ID | canlı mağaza |
| `price`, `sale_price`, `availability` | Sitedeki fiyat, indirim ve stok | canlı mağaza |
| `image_link` | Shopify CDN görseli (yoksa bu repodaki görsel) | canlı mağaza |
| `description` | "$27.46 per sq ft, 5.0 sq ft per box…" + malzeme, yüzey ve ölçü | canlı fiyat ÷ kutu ft² |
| `product_type` | `Natural Stone > Marble > Mosaic` | `data/import_update.csv` |
| `custom_label_0` | Desen: Checkerboard, Herringbone, Hexagon… (yoksa `None`) | metafield |
| `custom_label_1` | Renk ailesi: White, Grey, Black… | metafield |
| `custom_label_2` | Yüzey: Polished, Matte, Tumbled… | metafield |
| `custom_label_3` | Fiyat kademesi: `Value` (<$15/ft²), `Core` ($15–30), `Premium` (>$30), `Per Piece` | canlı fiyat |
| `custom_label_4` | `Outdoor` / `Indoor` | etiketler |
| `ad_link` (yalnızca Pinterest) | link + `utm_source=pinterest&utm_medium=paid_social&utm_campaign=catalog` | config |

Kademe sınırları `feed_config.json` içindeki `price_tiers_per_sqft` alanında.

**Güvenlik kilitleri:** Mağazadan hiç ürün gelmezse (ör. şifre açıldıysa) feed yazılmaz. Feed bir günde %20'den fazla küçülürse de yazılmaz; bu durumda Actions'ta hata görünür. Bilerek yapılan büyük bir silme için workflow yerelde `--allow-shrink` ile çalıştırılır.

---

## 3. Ürün setleri (Meta) ve ürün grupları (Pinterest)

İki platformda da aynı filtrelerle kurulur. Sayılar bugünkü katalogdan; fiyat kademeleri canlı fiyatla küçük farklar gösterebilir.

| Set | Filtre | Ürün |
|---|---|---|
| Tümü (trim hariç) | `product_type` "Trim" ve "Coaster" içermez | ~828 |
| Checkerboard | `custom_label_0` = Checkerboard | 126 |
| Herringbone & Chevron | `custom_label_0` ∈ Herringbone, Chevron | 46 |
| Şekilli mozaikler | `custom_label_0` ∈ Hexagon, Penny Round, Arabesque | 95 |
| Beyaz mermer | `product_type` "Marble" içerir **ve** `custom_label_1` = White | 361 |
| Mozaikler | `product_type` "Mosaic" içerir | 416 |
| Dış mekân | `custom_label_4` = Outdoor | 170 |
| Premium | `custom_label_3` = Premium | ~181 |

Trim parçaları (bordür, eşik, pervaz) tek başına reklam için zayıftır. Onları yalnızca yeniden hedeflemede ve sepete eklemiş kişilere göster.

---

## 4. Hedef kitleler

Her iki platformda da aynı kitleleri oluştur:

| Kitle | Tanım | Kullanım |
|---|---|---|
| Ürün görüntüleyenler 14g | ViewContent / pagevisit, son 14 gün | Katalog yeniden hedefleme |
| Sepete ekleyip almayanlar 30g | AddToCart, Purchase hariç | Katalog yeniden hedefleme (en yüksek öncelik) |
| Numune alanlar 60g | `SampleOrder` / `lead` | "Numuneni beğendin mi? Tam siparişi ver" |
| Satın alanlar 180g | Purchase | Soğuk kampanyalardan **hariç tut** |
| Site ziyaretçileri 180g | Tüm ziyaretler | Benzer kitle kaynağı |
| Müşteri listesi | Shopify → Customers → Export | Benzer kitle kaynağı, hariç tutma |
| Benzer kitle (Meta Lookalike / Pinterest Actalike) | Kaynak: satın alanlar + numune alanlar, ABD %1–3 | Soğuk kitle |

---

## 5. Başlangıç kampanya yapısı

**Meta**
1. `HH | META | Sales | Broad | Tümü` → Sales kampanyası, Advantage+ açık. Katalog reklamları ve tekil swatch görselleri birlikte. Optimizasyon: başta **Numune siparişi** (custom conversion), haftada ~50 satın alma olunca **Purchase**.
2. `HH | META | Retarget | Görüntüleyen+Sepet | Tümü` → Advantage+ catalog ads, yeniden hedefleme modu.
3. `HH | META | Sample→Order | Numune alanlar | Tümü` → numune alanlara tam sipariş mesajı.

**Pinterest**
1. `HH | PIN | Shopping | Prospecting | Checkerboard` (ve diğer ürün grupları ayrı ad group olarak). Pinterest'te desen bazlı arama güçlü; grupları ayırmak hangi desenin sattığını gösterir.
2. `HH | PIN | Shopping | Retarget | Tümü` → dinamik yeniden hedefleme.
3. `HH | PIN | Shopping | Seasonal | Outdoor` → Mart–Haziran arası.

Başlangıçta bütçenin ~%70'i soğuk kitleye, ~%30'u yeniden hedeflemeye gidebilir. İlk 2–3 hafta öğrenme dönemidir; bu sürede set ve bütçeleri sık değiştirme.

---

## 6. UTM ve isimlendirme

- **Meta**, reklam düzeyinde *URL parameters* alanı:
  `utm_source=meta&utm_medium=paid_social&utm_campaign={{campaign.name}}&utm_term={{adset.name}}&utm_content={{ad.name}}`
- **Pinterest** katalog reklamları feed'deki `ad_link` adresini kullanır. Standart pin reklamlarında hedef URL'ye `utm_source=pinterest&utm_medium=paid_social&utm_campaign=<kampanya>` ekle.
- İsim formatı: `HH | KANAL | Amaç | Kitle | Ürün seti` (ör. `HH | PIN | Shopping | Retarget | Tümü`). Shopify ve GA4 raporlarında bu isimler `utm_campaign` olarak görünür.

---

## 7. Bakım

- **Feed her sabah 05:17 UTC'de** yenilenir. `data/import_update.csv` veya feed kodu `main` dalında değiştiğinde de yenilenir. Değişiklik yoksa commit atılmaz.
- **Yeni ürün:** Matrixify sayfasına (`data/import_update.csv`) ekle; mağazada yayına girince ertesi sabah feed'e girer. Mağazada olup bu sayfada olmayan ürünler feed'e **girmez**; Actions günlüğünde `not_in_catalog` olarak listelenir.
- **Yerel çalıştırma ve test:**
  ```
  python3 marketing/build_feeds.py --store https://<mağaza-adresi>
  python3 -m unittest discover -s marketing
  ```

---

## 8. Reklam görselleri

`creatives/` klasöründe 15 konsept var. Her konsept dört boyutta:

| Dosya eki | Boyut | Nerede |
|---|---|---|
| `meta-1x1` | 1080×1080 | Meta akış, sağ sütun, carousel |
| `meta-4x5` | 1080×1350 | Meta akış (Facebook ve Instagram'da en çok alan kaplayan) |
| `meta-9x16` | 1080×1920 | Stories ve Reels. Yazı üst %14 ve alt %25 dışında; testler bunu kontrol eder |
| `pinterest-2x3` | 1000×1500 | Pinterest standart pin reklamı |

Konseptler:

| Tür | Konseptler | Amaç |
|---|---|---|
| Tekil ürün (8) | Dama, şevron, altıgen, arabesk, iki desenli mermer, Versailles, Rojo Alicante | Soğuk kitle; hangi ürünün tıklandığını görmek |
| Koleksiyon (4) | Checkerboard Floors, Herringbone & Chevron, Patterned Marble, Versailles Pattern | Soğuk kitle; Pinterest desen aramaları |
| Numune (1) | "See it in your own light." | **Numune siparişi** optimizasyonu, retargeting |
| Marka (2) | "Quarried, not printed.", "No two pieces alike." | Doğal taş ile baskılı porselen farkı |

Hızlı bakış için: `creatives/overview.jpg`.

**Metinler:** `creatives/ad-copy.csv` her konsept için şunları içerir: Meta *primary text*, *headline* ve *description*; Pinterest *title* ve *description*; hedef link (`/products/...` veya `/collections/...`, başına mağaza adresi eklenir). Metinler İngilizce (ABD pazarı). Karakter sınırları araç tarafından denetlenir.

**Kurulum:**
- **Meta:** Reklam düzeyinde 4:5 görseli yükle. *Placement asset customization* ile Stories/Reels için 9:16'yı, sağ sütun için 1:1'i seç. Dosya adları konsepti gösterir; reklam adı olarak konsept adını kullan (ör. `HH | META | Sales | Broad | Tümü` altında `checkerboard-nero-calacatta`).
- **Pinterest:** 2:3 görseli standart pin olarak yükle. Hedef URL'ye `?utm_source=pinterest&utm_medium=paid_social&utm_campaign=<kampanya>` ekle.
- İlk testte konsept başına bir reklam aç ve 1–2 hafta sonra kazananları koru. Görseller aynı tasarım dilinde olduğu için farkı ürün yaratır; böylece hangi taşın ve desenin ilgi çektiği net görünür.

**Yeni koleksiyonlar:** Herringbone & Chevron ve Patterned Marble reklamları `/collections/herringbone-chevron` ve `/collections/patterned-marble` adreslerine gider. Bu iki koleksiyon mağazada henüz yok. **Reklamları açmadan önce** `data/collections_ads.csv` dosyasını Matrixify ile içe aktar:
- **Herringbone & Chevron:** "Herringbone" veya "Chevron" etiketli 46 ürün.
- **Patterned Marble:** adı Stellare, Elara, Verona, Serratone ya da Sora ile başlayan 25 ürün.

**Değiştirme veya yeni konsept ekleme:** `marketing/creatives.json` içinde bir konsepti kopyala, `handle` veya `handles` ile metinleri değiştir, sonra şunu çalıştır:
```
pip install -r marketing/requirements.txt
python3 marketing/build_creatives.py              # hepsi
python3 marketing/build_creatives.py samples      # tek konsept
```
Ürün görselleri `images/` klasöründen olduğu gibi kullanılır; rötuş yapılmaz. Font olarak logonun yüzü Cormorant Garamond ve küçük etiketler için Jost kullanılır (ikisi de `brand/fonts/`, OFL lisanslı).

---

## 9. Oda render'ları (Pinterest)

NestTile satış verisindeki en çok satan doğal taşlardan Henry Harlow'da bulunanlar için 8 oda render'ı: banyo, duş, iki mutfak, lavabo odası, salon, giriş ve Japandi banyo. Karolar katalogdaki ölçüyle modellenir ve ürünün kendi fotoğrafıyla kaplanır, yani görseldeki ürün satılan ürünle aynıdır.

- **Görseller:** `creatives/rooms/` (temiz render ve Pinterest pini).
- **Pinterest toplu yükleme:** `python3 marketing/renders/pins.py --store https://<mağaza-adresi>` → `creatives/rooms/pins.csv`.
- **Yöntem, doğruluk, sınırlar ve yeniden üretme:** `marketing/renders/README.md`.
