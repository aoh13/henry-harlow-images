# Oda render'ları (Pinterest)

8 oda render'ı. Her biri Henry Harlow'un bir ürününü gerçek ölçüsü ve gerçek görünüşüyle gösterir. Pinterest'te gören biri aynı ürünü sipariş edebilir; render'daki karo kutudan çıkanla aynıdır.

| Oda | Ürün | Nerede, nasıl |
|---|---|---|
| `empress-green-bath` | Empress Green (Verde Alpi) Marble 12" x 12" — Matte | Arka duvar tavana kadar ve zemin; düz, 1/16" derz |
| `golden-coast-shower` | Golden Coast Slate 2" x 2" Mosaic | Duş duvarları ve tüm zemin; 12" levhada 2" taşlar |
| `rainbow-slate-kitchen` | Rainbow Slate 3" x 6" Tile — Tumbled | Tezgahtan tavana; yatay, yarım şaşırtma, 1/8" derz |
| `rosso-levanto-powder-room` | Rosso Levanto Leather Tumbled 12" x 12" | Bütün duvarlar ve zemin; düz, 1/8" derz |
| `walnut-travertine-living-room` | Walnut Travertine Brushed & Chiseled 18" x 18" | Tüm zemin; düz, 1/8" derz |
| `chakra-slate-mudroom` | Chakra Slate 3" x 6" Tile — Tumbled | Tüm zemin; 45° balıksırtı, 1/8" derz |
| `rojo-alicante-kitchen` | Rojo Alicante Marble — Polished 12" x 12" | Tüm zemin; 45° çapraz, 1/16" derz |
| `amazon-slate-japandi-bath` | Amazon Gray Slate 12" x 24" | Duş duvarı ve zemin; 1/3 şaşırtma, 1/8" derz |

Çıktılar `creatives/rooms/` klasöründe:
- `<oda>.jpg`: temiz render, 1000×1500. Site ve Meta için.
- `<oda>-pin.jpg`: tavana logo ve ürün adı eklenmiş Pinterest pini.
- `overview.jpg`: hepsine hızlı bakış.

## Ürün seçimi: NestTile satış verisi (1 Ocak – 28 Eylül 2026)

109 satış satırı katalogla önce SKU, sonra ad ve ölçüyle eşleştirildi. Aksesuarlar (priz kapakları, niş) ve trimler (bordür, eşik, pervaz) dışarıda bırakıldı.

- **Henry Harlow'da olan en çok satanlar render edildi:** Golden Coast Slate 2x2 mozaik (siparişte 2.), Rainbow Slate (1 numaralı aile; bizde 3x6 ve 1x1 var), Empress Green 12x12, Rosso Levanto 12x12, Walnut traverten 18x18, Chakra Slate 3x6, Rojo Alicante 12x12, Amazon Gray 12x24.
- **Henry Harlow'da olmayan en çok satanlar render edilmedi**, çünkü görseldeki ürünü satamayız: Zagora zellige, Kit-Kat porselen, Terrapetal, Palmetto terakota, Green Flat Jade Pebble, Dusty Rose 12x12, Emperador Dark 12x12, Rainbow Slate 2x2 mozaik, Golden Coast 4x4, Walnut traverten 4x4/3x6/12x12 ve Filled & Matte 18x18. Bunlar kataloğa eklenirse render'ları da yapılabilir.
- **Satışlardaki renk eğilimi:** yeşil (Empress Green, zellige yeşilleri, jade), toprak tonlu slate, bordo ve kırmızı (Rosso Levanto, Rojo Alicante) ve sıcak traverten. Odalar bu renklerle ve farklı oda tipleriyle kuruldu.

## Doğruluk nasıl sağlanıyor

1. **Ölçü:** Karonun boyu katalogdaki `nominal_size` alanından gelir. `products.py` bu alanı her ürün için kontrol eder; tutmazsa render başlamaz. Mozaiklerde levha 12" kabul edilir ve taş adımı fotoğraftaki taş sayısından gelir (ör. 2x2'de 6×6 taş: 1 7/8" taş + 1/8" derz).
2. **Görünüş:** Her karonun yüzeyi, o ürünün kendi katalog fotoğrafından kesilmiş taştır. Çoklu karo fotoğraflarında her karo ayrı parça olarak kullanılır (ör. 3x6'da 8 farklı karo, 2x2 mozaikte 36 farklı taş). Her karo bir parça alır ve rastgele döndürülür, ustanın döşediği gibi. Rötuş, boyama ya da üretilmiş doku yok.
3. **Döşeme:** Her karo ayrı bir taş olarak, ürünün derz genişliği ve kalınlığıyla (3/8") modellenir. Kenarlarda gerçek kesimler vardır ve döşeme duvara ortalanır, iki uçtaki kesik karolar eşit olur. Testler (`test_renders.py`) karoların hiçbir desende üst üste binmediğini ve derz payının ölçüyle tuttuğunu kontrol eder.
4. **Ölçek referansı:** Odadaki her şey standart ölçüde: tezgah 91 cm, lavabo dolabı 84 cm, küvet 165 cm. Göz karonun ölçeğini bunlarla doğru okur.

**Sınırlar (dürüstçe):**
- Tek karo fotoğrafı olan ürünlerde (Rosso Levanto, Rojo Alicante, Walnut 18x18, Amazon Gray) bütün karolar aynı fotoğrafın döndürülmüş hâlleridir. Gerçek taşta her karo farklıdır; varyasyon render'dakinden fazladır. Ürün sayfasındaki "taşın doğası gereği her parça farklıdır" notu bu yüzden önemli.
- Renk, ürün fotoğrafının rengidir. Render'ın ışığı (gün ışığı, AgX ton eşleme) onu bir oda fotoğrafındaki gibi gösterir. Numune önerisi bu yüzden pin metinlerinde var.
- Bunlar **3D render'dır**, yapay zekâ üretimi değil. Pin açıklamalarının hepsi "3D rendering made from the photograph of the tile we ship" der. Müşteri fotoğrafı gibi sunulmamalı.

## Pinterest'e yükleme

1. **Mağaza adresi:** `python3 marketing/renders/pins.py --store https://<mağaza-adresi>` komutu `creatives/rooms/pins.csv` dosyasını yazar. Her satırda başlık, açıklama, pano, ürün linki (UTM'li), anahtar kelimeler ve yayın tarihi (günde bir pin) bulunur.
2. **`main` dalı:** CSV'deki görsel adresleri `raw.githubusercontent.com/.../main/creatives/rooms/...` biçimindedir; bu yüzden dosyaların `main` dalında olması gerekir.
3. **Panolar:** Pinterest'te panoları önce aç: Green Marble Bathroom Ideas, Slate Shower Ideas, Kitchen Backsplash Ideas, Powder Room Ideas, Travertine Floor Ideas, Herringbone Floor Ideas, Marble Floor Ideas, Japandi Bathroom Ideas.
4. **Toplu yükleme:** Pinterest → **Create → Create Pin → Bulk create Pins → Upload .csv**. Pinterest'in sunduğu şablonla sütun adlarını karşılaştır; Pinterest bu formatı değiştirebiliyor.
5. **Reklam:** Aynı görseller Pinterest/Meta reklamlarında da kullanılabilir. Pin görseli zaten 2:3 formatında.

## Yeniden üretme veya oda ekleme

```
pip install bpy==4.2.0 Pillow numpy
python3 marketing/renders/render_room.py golden-coast-shower --preview   # 400x600, ~20 sn
python3 marketing/renders/render_room.py golden-coast-shower             # 1000x1500, ~15 dk (4 çekirdek CPU)
python3 marketing/renders/pins.py --store https://<mağaza-adresi>
python3 -m unittest discover -s marketing/renders
```

**Dosyalar:**
- `products.py`: ürünler, fotoğraftan kesim ve katalog kontrolü.
- `kit.py`: render ayarları, gün ışığı, malzemeler, oda kabuğu, döşeme motoru.
- `props.py`: mobilya ve dekor.
- `rooms.py`: odalar.
- `assets.py`: pencere dışındaki bahçe ve tablolar (Pillow ile üretilir; üçüncü taraf görsel yok).

**Yeni ürün eklemek:** `products.py`'deki `PRODUCTS` sözlüğüne fotoğrafın düzenini (`sheet`, `grid` ya da `single`), taş/karo ölçüsünü, derzi ve fotoğraftaki sınırları ekle. Ardından `rooms.py`'de yeni bir `@room` fonksiyonu yaz.
