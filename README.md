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