# Dokumentacja Wprowadzonych Zmian w Projekcie Mini-SIEM

## 1. Bezpieczeństwo i Uwierzytelnianie (Etap 1)

W tym etapie skupiono się na zabezpieczeniu tożsamości użytkowników oraz mechanizmie logowania, zgodnie z wytycznymi "Security First".

### `app/models.py`
Zaimplementowano bezpieczne przechowywanie haseł, aby uniknąć trzymania ich w formie tekstu jawnego (plain-text) w bazie danych.
* **`def set_password(self, password):`**
    * Wykorzystuje funkcję `generate_password_hash` z biblioteki `werkzeug.security`.
    * Tworzy bezpieczny skrót hasła (hash) z losową solą (salt) i zapisuje go w polu `password_hash`.
* **`def check_password(self, password):`**
    * Wykorzystuje funkcję `check_password_hash`.
    * Weryfikuje, czy podane hasło pasuje do zapisanego w bazie hasha, zwracając `True` lub `False`.

### `app/blueprints/auth.py`
* **`def login():`**
    * Obsługuje proces logowania użytkownika.
    * Pobiera użytkownika z bazy na podstawie nazwy.
    * Weryfikuje hasło metodą `check_password`.
    * W przypadku sukcesu: loguje użytkownika funkcją `login_user()`.
    * W przypadku błędu: wyświetla ogólny komunikat `flash("Niepoprawny login lub hasło")` (zgodnie z dobrymi praktykami nie zdradzamy, czy błąd dotyczy loginu czy hasła).

### `templates/login.html`
* Utworzono szablon formularza logowania dziedziczący po `base.html`.
* Dodano `{{ form.hidden_tag() }}` w celu ochrony przed atakami CSRF (Cross-Site Request Forgery).

---

## 2. Kontrola Dostępu (Access Control)

Zastosowano zasadę **Defense in Depth**, zabezpieczając nie tylko widok HTML, ale i punkty końcowe API.

### Dekorator `@login_required`
Dodano dekorator `flask_login.login_required` w kluczowych plikach:
* **`app/blueprints/ui.py`**: Zabezpieczono widok konfiguracji (`/config`), uniemożliwiając dostęp niezalogowanym użytkownikom.
* **`app/blueprints/api/hosts.py`**: Zabezpieczono wszystkie metody CRUD (Create, Read, Update, Delete). Nawet znając adres API, atakujący nie może usunąć ani modyfikować hostów bez aktywnej sesji.

---

## 3. Backend & Data Engineering (Etap 2)

Zaimplementowano serce systemu SIEM – proces pobierania, przetwarzania i analizy logów.

### `app/blueprints/api/hosts.py`
* **`def fetch_logs(host_id):`**
    * Zaimplementowano pełny proces **ETL** (Extract, Transform, Load):
        1.  **Zarządzanie Stanem:** Sprawdza lub tworzy wpis `LogSource` dla hosta.
        2.  **Pobieranie Przyrostowe:** Wywołuje `LogCollector` przekazując parametr `last_fetch_time`, aby pobierać tylko nowe logi (optymalizacja sieci i bazy danych).
        3.  **Forensics:** Zapisuje surowe logi do pliku **Parquet** za pomocą `DataManager` (wymóg informatyki śledczej - trwały zapis dowodów).
        4.  **Archiwizacja:** Rejestruje pobranie pliku w tabeli `LogArchive`.
        5.  **Analiza:** Przekazuje nazwę pliku do silnika analitycznego.

### `app/services/log_analyzer.py`
* **Threat Intelligence Logic (Silnik Analityczny):**
    * Otwiera plik Parquet przy użyciu biblioteki `pandas`.
    * Filtruje logi pod kątem zdarzeń bezpieczeństwa (np. `FAILED_LOGIN`, `WIN_FAILED_LOGIN`).
    * Porównuje adresy IP z bazą `IPRegistry` (Threat Intel).
    * **Automatyzacja:** Automatycznie dodaje nowe, nieznane adresy IP do rejestru ze statusem `UNKNOWN`.
    * **Eskalacja:** Jeśli IP ma status `BANNED` (czarna lista), podnosi priorytet alertu do `CRITICAL`.
    * Generuje wpisy w tabeli `Alert`.

---

## 4. Frontend Integration (Etap 3)

Zintegrowano interfejs użytkownika z nowym API, aby dane o zagrożeniach były prezentowane w czasie rzeczywistym.

### `app/static/js/api.js`
* Dodano funkcje asynchroniczne (wrapperów) do komunikacji z nowymi endpointami API:
    * `fetchAlerts()`: Pobiera listę ostatnich zagrożeń (JSON).
    * Funkcje CRUD dla IP: `fetchIPs()`, `createIP()`, `updateIP()`, `removeIP()`.

### `app/static/js/dashboard.js`
* Zaktualizowano logikę odświeżania dashboardu.
* Funkcja `refreshAlertsTable()` pobiera dane z `api.js` i dynamicznie generuje wiersze tabeli HTML.
* Zaimplementowano wizualizację powagi alertów:
    * **Czerwony wiersz:** Status `CRITICAL` (atak z zablokowanego IP).
    * **Żółty wiersz:** Status `WARNING` (podejrzane zdarzenie z nieznanego IP).

## WYMAGA ADMINA BY POBIERAC Z SECURITY

## 5. Finalne Poprawki i Uruchomienie (Etap 4)

W ostatniej fazie dokonano kluczowych poprawek integrujących wszystkie komponenty oraz dostosowano konfigurację do środowiska laboratoryjnego (Kali Linux).

### Backend (`app/blueprints/api/hosts.py`)
* **Naprawa błędu ETL (`fetch_logs`):** Poprawiono obsługę wartości zwracanej przez `DataManager.save_logs_to_parquet`. Funkcja zwraca teraz krotkę `(filename, count)`, co wcześniej powodowało błąd SQL `type 'tuple' is not supported`. Zastosowano rozpakowanie zmiennych: `filename, _ = ...`.
* **Implementacja API Rejestru IP:** Uzupełniono brakujące endpointy:
    * `GET /ips`: Zwraca listę zbanowanych adresów.
    * `POST /ips`: Dodaje nowe IP do czarnej listy (domyślnie status 'black').
    * `PUT /ips/<id>`: Pozwala zmienić status.
    * `DELETE /ips/<id>`: Usuwa wpis z rejestru.
* **Zmiana Konfiguracji SSH:** Przełączono domyślne uwierzytelnianie z kluczy SSH (Vagrant) na hasło, dostosowując system do maszyny wirtualnej Kali Linux (`user: kali`, `pass: SSH_PASSWORD z .env`).

### Log Collector (`app/services/log_collector.py`)
* **Ulepszone Regexy dla Linuxa:** Zaktualizowano wzorzec dla `sudo`, aby poprawnie wyciągał użytkownika i komendę.
* **Zmiana komendy źródłowej:** Zmieniono `journalctl -u ssh` na ogólne `journalctl`, aby wyłapywać również zdarzenia `sudo` (które nie są podpinane pod unit ssh).
* **Parsowanie JSON:** Dodano obsługę pola `_COMM` z logów systemd, co pozwala precyzyjniej identyfikować procesy.

### Frontend (`admin.js` i `dashboard.js`)
* **Panel Administratora:** Odkomentowano i aktywowano sekcję zarządzania "Threat Intel" (Rejestr IP). Administrator może teraz wyklikać dodanie adresu IP do czarnej listy.
* **Naprawa Licznika Alertów:** Poprawiono błąd w `dashboard.js`, gdzie kod oczekiwał pola `alerts_generated`, podczas gdy API zwracało `alerts`. Przycisk "Logi" teraz poprawnie zmienia kolor na czerwony po wykryciu zagrożenia.

## 6. Architektura i Przepływ Danych (Jak to działa?)

System Mini-SIEM działa w cyklu **ETL (Extract, Transform, Load)** z elementami analizy w czasie rzeczywistym.

### Krok 1: Konfiguracja (Control Plane)
Zarządzanie zasobami odbywa się poprzez REST API, zabezpieczone dekoratorem `@login_required`.
* **Frontend:** `admin.js` wysyła żądania JSON (`fetch`) do API.
* **Backend (Assets):** Plik `app/blueprints/api/hosts.py` -> endpoint `POST /hosts` zapisuje obiekt `Host` w bazie.
* **Backend (Threat Intel):** Plik `app/blueprints/api/hosts.py` -> endpoint `POST /ips` zapisuje obiekt `IPRegistry` (czarna lista).

### Krok 2: Ekstrakcja Danych (The ETL Controller)
Proces jest inicjowany przez użytkownika, ale sterowany przez backend.
* **Trigger:** `dashboard.js` wywołuje endpoint `POST /hosts/<id>/logs`.
* **Controller:** Funkcja `fetch_logs(host_id)` w `api/hosts.py` pełni rolę orkiestratora ETL.
* **State Management:** Kontroler sprawdza tabelę `LogSource` (model SQL). Pobiera wartość `last_fetch`, aby zażądać od kolektora tylko logów nowszych niż ostatnie sprawdzenie (logika przyrostowa).
* **Extract Logic:**
    * Klasa `RemoteClient` (`app/services/remote_client.py`) nawiązuje połączenie SSH.
    * Klasa `LogCollector` (`app/services/log_collector.py`) wykonuje zdalną komendę (np. `journalctl -o json`).

### Krok 3: Transformacja i Trwałość (Data Engineering)
Surowe dane są parsowane i utrwalane przed analizą.
* **Transform:** Metoda `LogCollector._parse_linux_message` używa wyrażeń regularnych (zdefiniowanych w słowniku `LINUX_PATTERNS`), aby przekształcić tekstowy log w ustandaryzowany słownik Python (`alert_type`, `source_ip`, `user`).
* **Load (Forensics):** Klasa `DataManager` zapisuje listę słowników bezpośrednio do pliku **Parquet** w katalogu `/storage`.
* **Metadata:** Kontroler `api/hosts.py` tworzy wpis w tabeli `LogArchive` (powiązanie: `host_id` <-> `filename`), rejestrując dowód w bazie danych.

### Krok 4: Silnik Analityczny (SIEM Core)
Logika wykrywania zagrożeń jest odseparowana od pobierania danych.
* **Engine:** Plik `app/services/log_analyzer.py`.
* **Input:** Metoda `analyze_parquet(filename)` ładuje plik Parquet do **Pandas DataFrame** (wysoka wydajność filtrowania).
* **Logic (Static):** Filtrowanie wierszy gdzie `alert_type` in `['FAILED_LOGIN', 'SUDO_USAGE', ...]`.
* **Logic (Dynamic/CTI):** Iteracja po wykrytych incydentach i sprawdzanie `IPRegistry.query.filter_by(ip=source_ip)`.
    * Jeśli `status == 'BANNED'` -> Ustawia `severity='CRITICAL'`.
    * Jeśli IP nie istnieje -> Dodaje je do bazy jako `UNKNOWN` (automatyczne uczenie).
* **Output:** Zapis obiektów `Alert` do bazy SQL.

### ✅ A. Bezpieczeństwo (Security First)
* **Hashowanie haseł:** [x] Zaimplementowano `werkzeug.security` (PBKDF2+SHA256). Hasła nie są przechowywane jawnym tekstem.
* **Ochrona API:** [x] Wszystkie endpointy (`GET`, `POST`, `PUT`, `DELETE`) w `api/hosts.py` chronione dekoratorem `@login_required`.
* **Defense in Depth:** [x] Ochrona CSRF w formularzach (`hidden_tag`) oraz bezpieczne komunikaty błędów logowania.

### ✅ B. Architektura i Logika (SIEM & Forensics)
* **Informatyka Śledcza:** [x] Surowe logi są zapisywane do plików **Parquet** (folder `storage/`) przed analizą. Zachowano ciągłość dowodową.
* **Threat Intelligence:** [x] Silnik `LogAnalyzer` automatycznie koreluje IP z bazą `IPRegistry`.
    * Status `BANNED` -> Alert `CRITICAL`.
    * Nowe IP -> Automatyczne dodanie jako `UNKNOWN`.
* **ETL & Log Collector:** [x] Zaimplementowano pobieranie przyrostowe (`last_fetch_time`) oraz regexy obsługujące logi systemowe Linux (SSH/Sudo) i Windows (EventID 4625).

### ❌ D. Zadania Dodatkowe ("Gwiazdki") - Niezrealizowane
* [ ] Cross-Host Correlation (korelacja ataków między różnymi hostami).
* [ ] Wykresy statystyczne (Chart.js) na Dashboardzie.
* [ ] Dynamiczny tryb ciemny (Dark Mode).
* [ ] Pełne zabezpieczenie CSRF dla zapytań API (fetch).