import urllib.request
import urllib.error
import time
import os
import json
import re

from env_loader import load_env, require_env, require_env_int
from telegram_notifications import send_telegram_message

# ================= AYARLAR =================
# TCDD API Token (Chrome Network sekmesinden kopyaladığın Authorization)
# SÜRESİ DOLARSA BURAYI GÜNCELLE!
load_env()
TOKEN = require_env("TCDD_TOKEN")

# Yolcu Bilgileri (Rezerve için gereklidir)
YOLCU = {
    "name": require_env("PASSENGER_NAME"),
    "lastName": require_env("PASSENGER_LAST_NAME"),
    "birthDate": require_env("PASSENGER_BIRTH_DATE"),
    "gender": require_env("PASSENGER_GENDER"),
    "identityNumber": require_env("PASSENGER_IDENTITY_NUMBER"),
    "email": require_env("PASSENGER_EMAIL"),
    "phoneAreaCode": require_env("PASSENGER_PHONE_AREA_CODE"),
    "phoneNumber": require_env("PASSENGER_PHONE_NUMBER")
}

def require_env_int_list(key):
    raw_value = require_env(key).strip()
    try:
        values = (
            json.loads(raw_value)
            if raw_value.startswith("[")
            else re.split(r"[,\s;]+", raw_value)
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{key} env degiskeni gecerli bir liste olmali.") from exc

    if not isinstance(values, list):
        raise RuntimeError(f"{key} env degiskeni liste olmali.")

    parsed_values = []
    for value in values:
        if isinstance(value, str):
            value = value.strip()
        if value in ("", None):
            continue

        try:
            parsed_values.append(int(value))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"{key} env degiskeni sayi listesi olmali.") from exc

    if not parsed_values:
        raise RuntimeError(f"{key} env degiskeni en az bir sayi icermeli.")

    return parsed_values

def require_env_str_list(key):
    raw_value = require_env(key).strip()
    try:
        values = (
            json.loads(raw_value)
            if raw_value.startswith("[")
            else re.split(r"[,\s;]+", raw_value)
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{key} env degiskeni gecerli bir liste olmali.") from exc

    if not isinstance(values, list):
        raise RuntimeError(f"{key} env degiskeni liste olmali.")

    parsed_values = [str(value).strip() for value in values if str(value).strip()]
    if not parsed_values:
        raise RuntimeError(f"{key} env degiskeni en az bir deger icermeli.")

    return parsed_values

def require_env_bool(key):
    value = require_env(key).strip().lower()
    if value in ("1", "true", "yes", "y", "evet"):
        return True
    if value in ("0", "false", "no", "n", "hayir"):
        return False

    raise RuntimeError(f"{key} env degiskeni true/false olmali.")

# Arama Kriterleri
ROUTE = {
    "departureStationId": require_env_int("FROM_STATION_ID"),
    "departureStationName": require_env("FROM_STATION_LABEL"),
    "arrivalStationId": require_env_int("TO_STATION_ID"),
    "arrivalStationName": require_env("TO_STATION_LABEL"),
    "departureDate": require_env("DEPARTURE_DATE")
}

SEARCH_PAYLOAD = {
    "searchRoutes": [ROUTE],
    "passengerTypeCounts": [
        {
            "id": require_env_int("PASSENGER_TYPE_ID"),
            "count": require_env_int("PASSENGER_COUNT"),
        }
    ],
    "searchReservation": require_env_bool("SEARCH_RESERVATION"),
    "blTrainTypes": require_env_str_list("TRAIN_TYPES")
}

TARGET_TRAIN_IDS = require_env_int_list("TARGET_TRAIN_IDS")
PASSENGER_TYPE_COUNTS = SEARCH_PAYLOAD["passengerTypeCounts"]
PRIMARY_PASSENGER_TYPE_ID = PASSENGER_TYPE_COUNTS[0]["id"]
TOTAL_PASSENGER_COUNT = sum(passenger_type["count"] for passenger_type in PASSENGER_TYPE_COUNTS)
FROM_STATION_ID = ROUTE["departureStationId"]
TO_STATION_ID = ROUTE["arrivalStationId"]
BOT_NAME = f"TCDD {ROUTE['departureStationName']}-{ROUTE['arrivalStationName']} Botu"
notified_error_keys = set()

BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Authorization": TOKEN,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3.1 Safari/605.1.15",
    "unit-id": "3895",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Origin": "https://ebilet.tcddtasimacilik.gov.tr"
}
# ===========================================

def route_label():
    route = SEARCH_PAYLOAD["searchRoutes"][0]
    return f"{route.get('departureStationName', '-')} -> {route.get('arrivalStationName', '-')}"

def current_time_label():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def positive_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def target_train_identifiers():
    return {
        train_id
        for train_id in (positive_int(value) for value in TARGET_TRAIN_IDS)
        if train_id
    }

def target_train_label():
    return ", ".join(str(train_id) for train_id in TARGET_TRAIN_IDS) or "-"

def notify_error(title, endpoint, detail, http_code=None, explanation=None, dedupe_key=None):
    key = dedupe_key or (title, endpoint, http_code)
    if key in notified_error_keys:
        return

    notified_error_keys.add(key)
    lines = [
        title,
        f"Bot: {BOT_NAME}",
        f"Rota: {route_label()}",
        f"Endpoint: {endpoint}",
    ]
    if http_code:
        lines.append(f"HTTP: {http_code}")
    if explanation:
        lines.append(f"Aciklama: {explanation}")
    lines.extend([
        f"Zaman: {current_time_label()}",
        f"Detay: {detail[:500] if detail else '-'}",
    ])
    send_telegram_message("\n".join(lines))

def build_search_started_notification():
    route = SEARCH_PAYLOAD["searchRoutes"][0]
    train_types = ", ".join(SEARCH_PAYLOAD.get("blTrainTypes", [])) or "-"
    return "\n".join([
        "TCDD BOT - ARAMA BASLADI",
        f"Bot: {BOT_NAME}",
        f"Rota: {route_label()}",
        f"Kalkis: {route.get('departureDate', '-')}",
        f"Hedef trenler: {target_train_label()}",
        f"Yolcu sayisi: {TOTAL_PASSENGER_COUNT}",
        f"Tren tipi: {train_types}",
        f"Zaman: {current_time_label()}",
    ])

def api_request(url, payload):
    """Genel API İstek Atıcı"""
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=BASE_HEADERS, method='POST')
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                resp_text = response.read().decode('utf-8')
                if not resp_text: return {}
                return json.loads(resp_text)
    except urllib.error.HTTPError as e:
        # TCDD API url'sinden son kısmını bulalım sadece terminali kirletmesin
        endpoint = url.split('/')[-1].split('?')[0]

        if e.code == 400:
            # 400 Koltuk Seçme esnasında dönüyorsa o koltuk dolmuştur (sessiz geç)
            if "select-seat" not in url:
                error_body = e.read().decode('utf-8')
                notify_error(
                    "TCDD BOT - API HATASI",
                    endpoint,
                    error_body,
                    http_code=e.code,
                    explanation="TCDD API istegi reddetti.",
                )
                print(f"[-] [HTTP 400] {endpoint} isteği reddedildi! Detay: {error_body}")
        else:
            error_body = e.read().decode('utf-8')
            if e.code in (401, 403):
                notify_error(
                    "TCDD BOT - E-BILET TOKEN HATASI",
                    endpoint,
                    error_body,
                    http_code=e.code,
                    explanation="E-bilet/TCDD API token gecersiz veya suresi dolmus olabilir. Token'i yenilemek lazim.",
                )
            else:
                notify_error(
                    "TCDD BOT - API HATASI",
                    endpoint,
                    error_body,
                    http_code=e.code,
                    explanation="TCDD API beklenmeyen hata dondu.",
                )
            print(f"[!] [HTTP {e.code}] Beklenmeyen Hata ({endpoint}): {error_body}")

    except Exception as e:
        endpoint = url.split('/')[-1].split('?')[0]
        notify_error(
            "TCDD BOT - ISTEK HATASI",
            endpoint,
            str(e),
            explanation="TCDD API istegi gonderilirken hata olustu.",
        )
        print(f"[x] İSTEK HATASI ({endpoint}): {e}")

    return None

def check_tickets(json_data):
    """Ana aramadan verileri, trainId, vagonId vs toplar"""
    tickets = []
    target_identifiers = target_train_identifiers()
    train_legs = json_data.get("trainLegs", [])
    if not isinstance(train_legs, list): return tickets

    for leg in train_legs:
        if not isinstance(leg, dict): continue
        for availability in leg.get("trainAvailabilities", []):
            if not isinstance(availability, dict): continue
            for train in availability.get("trains", []):
                if not isinstance(train, dict): continue

                train_identifiers = {
                    positive_int(train.get("id")),
                    positive_int(train.get("number")),
                }
                if target_identifiers and not train_identifiers.intersection(target_identifiers):
                    continue

                train_id = train.get("id")

                # Fiyat, Koltuk tipleri detayları
                fare_infos = train.get("availableFareInfo", [])
                if not isinstance(fare_infos, list): continue

                for fare_info in fare_infos:
                    if not isinstance(fare_info, dict): continue
                    for cabin in fare_info.get("cabinClasses", []):
                        if not isinstance(cabin, dict): continue

                        cabin_info = cabin.get("cabinClass", {})
                        if not isinstance(cabin_info, dict): continue
                        cabin_name = cabin_info.get("name", "")
                        availability_count = positive_int(cabin.get("availabilityCount", 0))

                        fare_family = fare_info.get("fareFamily", {})
                        fare_family_id = fare_family.get("id", 1) if isinstance(fare_family, dict) else 1
                        cabin_class_id = cabin_info.get("id", 2)

                        if cabin_name == "EKONOMİ" and availability_count > 0:
                            # Hangi Vagon?
                            # Bu sınıf ID'sine (Örn: Business=1, Ekonomi=4) uygun vagonu cars listesinden bulalım
                            target_car_id = None
                            cars = train.get("cars", [])
                            if not isinstance(cars, list): continue

                            for car in cars:
                                if not isinstance(car, dict): continue
                                availabilities = car.get("availabilities", [])
                                if not isinstance(availabilities, list): continue

                                for av in availabilities:
                                    if not isinstance(av, dict): continue
                                    # ✅ BUGFIX: Sadece EKONOMİ vagonuna bak, BUSİNESS vs. atlama
                                    av_cabin = av.get("cabinClass", {})
                                    if not isinstance(av_cabin, dict): continue
                                    if av_cabin.get("name", "") != "EKONOMİ": continue

                                    if positive_int(av.get("availability", 0)) > 0:
                                        pricing_list = av.get("pricingList", [])
                                        if isinstance(pricing_list, list):
                                            for pl in pricing_list:
                                                if not isinstance(pl, dict): continue
                                                pricing_availability = positive_int(pl.get("availability", 0))
                                                if pricing_availability > 0:
                                                    target_car_id = car.get("id")
                                                    bc = pl.get("bookingClass", {})
                                                    booking_class_id = bc.get("id", 1) if isinstance(bc, dict) else 1
                                                    # cabinClassId'yi pricingList'ten al (daha güvenilir)
                                                    pl_cabin_class_id = pl.get("cabinClassId", cabin_class_id)

                                                    tickets.append({
                                                        "trainId": train_id,
                                                        "trainNumber": train.get("number"),
                                                        "trainName": train.get("name") or train.get("commercialName"),
                                                        "trainCarId": target_car_id,
                                                        "bookingClassId": booking_class_id,
                                                        "fareFamilyId": fare_family_id,
                                                        "cabinClassId": pl_cabin_class_id,
                                                        "sinif": cabin_name,
                                                        "bos_sayisi": pricing_availability,
                                                        "fiyat": cabin.get("minPrice"),
                                                        "para_birimi": cabin.get("minPriceCurrency")
                                                    })
                                                    break
                                        if target_car_id: break
                                if target_car_id: break
    return tickets

def alert_mac():
    os.system('osascript -e \'display notification "BİLET REZERVE EDİLDİ! PNR SMS/MAIL GELDİ" with title "TCDD BOT" sound name "Glass"\'')
    for _ in range(1):
        os.system('afplay /System/Library/Sounds/Hero.aiff')
        os.system('say "İşlem Tamam. Bilet rezerve edildi."')
        time.sleep(1)

def build_success_notification(ticket, pnr_no, locked_seat):
    route = SEARCH_PAYLOAD["searchRoutes"][0]
    train_name = ticket.get("trainName") or (
        f"Tren {ticket.get('trainNumber')}" if ticket.get("trainNumber") else "TCDD treni"
    )
    departure = route.get("departureStationName", "-")
    arrival = route.get("arrivalStationName", "-")
    departure_date = route.get("departureDate", "-")
    pnr_text = pnr_no or "PNR cevabi alindi, numara parse edilemedi"
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    return "\n".join([
        "TCDD BOT - BASARILI REZERVASYON",
        f"Sinyal: {train_name} icin uygun bilet bulundu",
        f"Rota: {departure} -> {arrival}",
        f"Kalkis: {departure_date}",
        f"Sinif: {ticket.get('sinif', '-')}",
        f"Fiyat: {ticket.get('fiyat', '-') if ticket.get('fiyat') is not None else '-'} {ticket.get('para_birimi', '')}".strip(),
        f"Bos koltuk: {ticket.get('bos_sayisi', '-')}",
        f"Kilitlenen koltuk: {locked_seat or '-'}",
        f"PNR: {pnr_text}",
        f"Zaman: {now}",
        "Aciklama: PNR/rezervasyon basariyla olusturuldu. SMS/Mail kontrol edin.",
    ])

def main():
    print("🚀 TCDD OTONOM BOTU BAŞLATILDI 🚀")
    print("Her 1 saniyede bir tarama yapılacak. Boş yer bulunduğunda otomatik PNR oluşturulacak!")
    send_telegram_message(build_search_started_notification())

    url_search = "https://web-api-prod-ytp.tcddtasimacilik.gov.tr/tms/train/train-availability?environment=dev&userId=1"
    url_seatmap = "https://web-api-prod-ytp.tcddtasimacilik.gov.tr/tms/seat-maps/load-by-train-id?environment=dev&userId=1"
    url_select = "https://web-api-prod-ytp.tcddtasimacilik.gov.tr/tms/inventory/select-seat?environment=dev&userId=1"
    url_pnr = "https://web-api-prod-ytp.tcddtasimacilik.gov.tr/crs/rail-booking/create-pnr?environment=dev&userId=1"

    while True:
        try:
            data = api_request(url_search, SEARCH_PAYLOAD)
            if data:
                tickets = check_tickets(data)

                if tickets:
                    print("\n🔥 BİLET BULUNDU! OTOMATİK SATIN ALMA PROTOKOLÜ BAŞLATILIYOR... 🔥")

                    t = tickets[0] # İlk bulduğu bileti al
                    train_id = t["trainId"]
                    car_id = t["trainCarId"]

                    # 1. KOLTUK HARİTASI ÇEK VE TÜM GEÇERLİ KOLTUK NUMARALARINI TOPLA
                    print("-> Vagon Haritası Çekiliyor...")
                    seat_payload = {
                        "fromStationId": FROM_STATION_ID,
                        "toStationId": TO_STATION_ID,
                        "trainId": train_id,
                        "legIndex": 0
                    }
                    map_data = api_request(url_seatmap, seat_payload)
                    if map_data is None:
                        print("[-] Vagon haritası alınamadı. Segment/station uyumsuz olabilir; koltuk seçme denenmeden aramaya devam ediliyor...")
                        continue

                    # Vagon haritasından koltuk numaralarını çıkar (1A, 1B, 2A...)
                    possible_seats = []
                    if map_data and "seatMaps" in map_data and isinstance(map_data["seatMaps"], list):
                        for sm in map_data["seatMaps"]:
                            if not isinstance(sm, dict): continue
                            inner_maps = sm.get("seatMaps", [])
                            if not isinstance(inner_maps, list): continue
                            for inner_sm in inner_maps:
                                if not isinstance(inner_sm, dict): continue
                                sn = inner_sm.get("seatNumber", "")
                                if isinstance(sn, str) and sn and len(sn) <= 3:
                                    possible_seats.append(sn)

                    # Vagon haritası gelmezse standart koltukları salla
                    if not possible_seats:
                        possible_seats = [f"{n}{l}" for n in range(1, 20) for l in ['A','B','C','D']]

                    print(f"-> Haritadan okunabilen koltuklar: {len(possible_seats)} adet. Hızlı deneme başlıyor...")

                    # 2. KOLTUKLARI RAPID-FIRE SEÇMEYE ÇALIŞ (Boş olan kilitlenecek)
                    allocation_id = None
                    locked_seat = None

                    for seat in possible_seats:
                        sel_payload = {
                            "trainCarId": car_id,
                            "fromStationId": FROM_STATION_ID,
                            "toStationId": TO_STATION_ID,
                            "gender": YOLCU["gender"],
                            "seatNumber": seat,
                            "passengerTypeId": PRIMARY_PASSENGER_TYPE_ID,
                            "totalPassengerCount": TOTAL_PASSENGER_COUNT,
                            "fareFamilyId": 0
                        }
                        # Kilit isteği
                        resp = api_request(url_select, sel_payload)
                        # Eğer doluysa 400 Bad Request döner `api_request` None verir.
                        # Eğer boşsa 200 döner ve içinde allocationId olur!
                        if resp and "allocationId" in resp:
                            allocation_id = resp["allocationId"]
                            locked_seat = seat
                            print(f"[✓] KOLTUK KİLİTLENDİ! Mükemmel! (Koltuk No: {seat}, Kilit ID: {allocation_id})")
                            break # Koltuğu bulduk, döngüden çık!

                    # 3. PNR OLUŞTURMA İŞLEMİ (EĞER KOLTUK KİLİTLENDİYSE)
                    if allocation_id:
                        print("-> PNR Rezervasyonu Oluşturuluyor. Lütfen bekleyin...")

                        pnr_payload = {
                          "lang": "TR",
                          "allocationId": allocation_id,
                          "passengers": [
                            {
                              "name": YOLCU["name"],
                              "lastName": YOLCU["lastName"],
                              "birthDate": YOLCU["birthDate"],
                              "gender": YOLCU["gender"],
                              "typeId": PRIMARY_PASSENGER_TYPE_ID,
                              "contact": False,
                              "phoneCountryCode": "90",
                              "phoneAreaCode": YOLCU["phoneAreaCode"],
                              "phoneNumber": YOLCU["phoneNumber"],
                              "email": YOLCU["email"],
                              "countryId": 1,
                              "identityNumber": YOLCU["identityNumber"],
                              "loyaltyNumber": "",
                              "gdpr": False,
                              "passengerMultiLegSeatSelections": [
                                [
                                  {
                                    "trainCarId": car_id,
                                    "seatNumber": locked_seat,
                                    "fromStationId": FROM_STATION_ID,
                                    "toStationId": TO_STATION_ID,
                                    "lockForDate": int(time.time() * 1000) + 600000, # Şimdiki zaman + 10dk
                                    "selectedBookingClassId": t["bookingClassId"],
                                    "selectedFareFamilyId": t["fareFamilyId"],
                                    "selectedCabinClassId": t["cabinClassId"]
                                  }
                                ]
                              ]
                            }
                          ],
                          "preReservation": False
                        }

                        pnr_resp = api_request(url_pnr, pnr_payload)

                        if pnr_resp:
                            print("=======================================")
                            print("✅ İŞLEM BAŞARIYLA TAMAMLANDI! (PNR/REZERVASYON YARATILDI)")

                            # API'den gelen cevapta pnrNumber'ı ayıklayıp ekrana basalım
                            pnr_no = None
                            if isinstance(pnr_resp, dict):
                                # TCDD cevabı yapısını tahmin ederek çekiyoruz, PNR numarası locator key'i ile dönüyor
                                pnr_no = pnr_resp.get("locator") or pnr_resp.get("pnrNumber") or pnr_resp.get("pnr") or pnr_resp.get("pnrNo")
                                if not pnr_no and "pnrResponse" in pnr_resp and isinstance(pnr_resp["pnrResponse"], dict):
                                    pnr_no = pnr_resp["pnrResponse"].get("pnrNumber") or pnr_resp["pnrResponse"].get("pnr")

                                if pnr_no:
                                    print(f"🎫 PNR NUMARANIZ: {pnr_no}")
                                else:
                                    print(f"🎫 PNR CEVABI (RAW): {pnr_resp}")
                            else:
                                print(f"🎫 PNR CEVABI YOK (Veya Parse Edilemedi): {pnr_resp}")

                            print("Lütfen TCDD SMS/Mail mesajlarınızı kontrol edin.")
                            notification_message = build_success_notification(t, pnr_no, locked_seat)
                            send_telegram_message(notification_message)
                            print("=======================================")

                            # Alarm çal ve sistemi bitir (Sürekli alım yapmaması için)
                            alert_mac()
                            break
                        else:
                            print("[-] PNR Rezervasyonu TCDD Tarafından Reddedildi! (Bu koltuk seçilememektedir, cinsiyet vb. engel). Aramaya devam ediliyor...")
                            # Döngünün başa sarması ve taranmaya devam etmesi için dışarıdan devam etmesine izin veriyoruz
                            continue
                    else:
                        print("[-] Uygun koltuklar denenirken sistem tarafından boş koltuk kalmadı(Zaten başkası kapmış). Aramaya devam ediliyor...")
                else:
                    t_str = time.strftime("%H:%M:%S")
                    print(f"[{t_str}] Tarandı: Bilet yok. Yeni tarama için bekleniyor...")
        except Exception as e:
            notify_error(
                "TCDD BOT - CALISMA HATASI",
                "main-loop",
                str(e),
                explanation="Bot ana dongude beklenmeyen hata aldi.",
            )
            print(f"Hata: {e}")

        time.sleep(1)

if __name__ == "__main__":
    main()
