# TCDD Bot

Env ile ayarlanan, rota ve tren listesini koda gommeden calisan TCDD bilet takip/rezervasyon botu.

Bot TCDD web API'sine belirlenen rota, tarih, yolcu tipi ve tren tipleriyle istek atar. Uygun ekonomi koltuk bulursa koltugu kilitlemeyi ve PNR/rezervasyon olusturmayi dener. Basarili olursa terminale yazar, macOS bildirimi verir ve Telegram ayarlari doluysa Telegram mesaji gonderir.

## Temel Mantik

- Kodda rota, istasyon, tarih ve hedef tren listesi hardcoded degildir.
- Zorunlu env eksikse bot baslamaz ve `.env dosyasina ekle/doldur` diye hata verir.
- `.env` icinde satir basi yorumlar ve quote disindaki inline yorumlar desteklenir.
- `TARGET_TRAIN_IDS` gelen TCDD cevabindaki `train.id` veya `train.number` alanlarindan biriyle eslesirse tren hedef sayilir.
- Telegram opsiyoneldir. Token/chat id yoksa bildirim gonderilmez, bot normal calismaya devam eder.

## Kurulum

```bash
cp .env.example .env
nano .env
```

`.env` dosyasini kendi TCDD inspect verilerin ve yolcu bilgilerinle doldur. `.env` git'e eklenmez; token ve kimlik bilgilerini repoya koyma.

## Env Ayarlari

String degerleri tirnak icinde, sayisal degerleri tirnaksiz yazmak daha okunur:

```env
FROM_STATION_LABEL="ANKARA GAR"
FROM_STATION_ID=98
TARGET_TRAIN_IDS="81021,81459,81033,81023"
```

Inline yorum yazabilirsin:

```env
FROM_STATION_ID=98                      # departureStationId
FROM_STATION_LABEL="ANKARA GAR"         # departureStationName
```

### Zorunlu Alanlar

| Env | Ne ise yarar |
| --- | --- |
| `TCDD_TOKEN` | TCDD request'indeki `Authorization` / bearer token |
| `PASSENGER_NAME` | PNR yolcu adi |
| `PASSENGER_LAST_NAME` | PNR yolcu soyadi |
| `PASSENGER_BIRTH_DATE` | PNR dogum tarihi |
| `PASSENGER_GENDER` | Koltuk secimi ve PNR icin cinsiyet |
| `PASSENGER_IDENTITY_NUMBER` | PNR kimlik numarasi |
| `PASSENGER_EMAIL` | PNR email |
| `PASSENGER_PHONE_AREA_CODE` | Telefon ilk 3 hane |
| `PASSENGER_PHONE_NUMBER` | Telefon kalan haneler |
| `PASSENGER_TYPE_ID` | TCDD `passengerTypeCounts.id`, `passengerTypeId`, `typeId` |
| `PASSENGER_COUNT` | TCDD yolcu sayisi. Su an bot pratikte 1 kisi icin tasarlandi |
| `FROM_STATION_ID` | `departureStationId` |
| `FROM_STATION_LABEL` | `departureStationName` |
| `TO_STATION_ID` | `arrivalStationId` |
| `TO_STATION_LABEL` | `arrivalStationName` |
| `DEPARTURE_DATE` | `departureDate`; TCDD inspect'te ne geliyorsa onu yaz |
| `SEARCH_RESERVATION` | `searchReservation`; normal bilet aramasinda genelde `false` |
| `TRAIN_TYPES` | `blTrainTypes`; tek deger veya virgullu liste |
| `TARGET_TRAIN_IDS` | Bakilacak tren id/numara listesi |

### Opsiyonel Telegram Alanlari

| Env | Ne ise yarar |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | BotFather'dan aldigin Telegram bot token |
| `TELEGRAM_CHAT_ID` | Bildirim gidecek chat id |

Telegram bilgileri doluysa bot arama baslangicinda, hata durumlarinda ve basarili PNR olustugunda mesaj yollar.

## TCDD Verilerini Nereden Alacaksin?

1. TCDD e-bilet sitesinde normal arama yap.
2. Browser DevTools > Network ac.
3. `train-availability` request'ini bul.
4. Request payload icinden sunlari `.env` dosyasina tasiyabilirsin:

```text
departureStationId      -> FROM_STATION_ID
departureStationName    -> FROM_STATION_LABEL
arrivalStationId        -> TO_STATION_ID
arrivalStationName      -> TO_STATION_LABEL
departureDate           -> DEPARTURE_DATE
searchReservation       -> SEARCH_RESERVATION
blTrainTypes            -> TRAIN_TYPES
passengerTypeCounts.id  -> PASSENGER_TYPE_ID
```

`TARGET_TRAIN_IDS` icin response tarafindaki trenlerin `id` veya `number` degerlerini kullanabilirsin. Liste formati:

```env
TARGET_TRAIN_IDS="81021,81459,81033,81023"
```

`TRAIN_TYPES` birden fazla olacaksa:

```env
TRAIN_TYPES="YHT,TURISTIK_TREN"
```

## Lokal Calistirma

```bash
python3 -u bot/tcdd_bot.py
```

Telegram test mesaji icin:

```bash
python3 bot/test_telegram.py
```

## Docker Ile Calistirma

```bash
docker compose up -d --build
```

Loglari izlemek icin:

```bash
docker compose logs -f tcdd-bot
```

Durdurmak icin:

```bash
docker compose down
```

`docker-compose.yml` tek servis calistirir: `tcdd-bot`. Servis `.env` dosyasini okur ve `python -u bot/tcdd_bot.py` komutunu baslatir.

## Hata Notlari

- `X env degiskeni zorunlu. .env dosyasina ekle/doldur.`: Zorunlu alan eksik veya bos.
- `X env degiskeni sayi olmali.`: Sayi beklenen alana string yazilmis.
- `TARGET_TRAIN_IDS env degiskeni sayi listesi olmali.`: Tren listesinde sayi olmayan deger var.
- `SEARCH_RESERVATION env degiskeni true/false olmali.`: `true`, `false`, `1`, `0`, `yes`, `no`, `evet`, `hayir` degerlerinden birini kullan.
- TCDD `401/403` donerse token suresi dolmus olabilir; yeni bearer token alip `.env` icinde `TCDD_TOKEN` guncelle.
- Vagon haritasi alinmazsa rota/tarih/segment uyumsuz olabilir; inspect verilerini yeniden kontrol et.

## Su Anki Sinirlar

- Otomatik secim mantigi ekonomi kabin uzerinden ilerliyor.
- `PASSENGER_COUNT=1` disi senaryolar kodda tam garanti degil.
- Endpointler, `unit-id`, `User-Agent`, `phoneCountryCode`, `countryId` gibi TCDD/protokol sabitleri kodda duruyor.
- macOS lokal alarmi `osascript`, `afplay` ve `say` kullanir; Docker/VDS tarafinda Telegram bildirimi asil sinyaldir.
