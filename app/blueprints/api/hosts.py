import time
from flask import Blueprint, jsonify, request, current_app
from datetime import timezone, datetime
import os
from flask_login import login_required
from app.models import Host, LogSource, LogArchive, Alert, IPRegistry
from app.services.remote_client import RemoteClient
from app.services.win_client import WinClient
from app.services.log_collector import LogCollector
from app.services.data_manager import DataManager
from app.services.log_analyzer import LogAnalyzer
from app.extensions import db

api_bp = Blueprint("api_hosts", __name__)

# --- CRUD HOSTS (GOTOWE - ABY UI DZIAŁAŁO) ---

@api_bp.route("/hosts", methods=["GET"])
@login_required
def get_hosts():
    hosts = Host.query.all()
    return jsonify([h.to_dict() for h in hosts])

@api_bp.route("/hosts", methods=["POST"])
@login_required
def add_host():
    data = request.get_json()
    if not data: return jsonify({"error": "Brak danych"}), 400
    if Host.query.filter_by(ip_address=data.get("ip_address")).first():
        return jsonify({"error": "IP musi być unikalne"}), 409
    new_host = Host(hostname=data.get("hostname"), ip_address=data.get("ip_address"), os_type=data.get("os_type"))
    db.session.add(new_host)
    db.session.commit()
    return jsonify(new_host.to_dict()), 201

@api_bp.route("/hosts/<int:host_id>", methods=["DELETE"])
@login_required
def delete_host(host_id):
    host = Host.query.get_or_404(host_id)
    db.session.delete(host)
    db.session.commit()
    return jsonify({"message": "Usunięto hosta"}), 200

@api_bp.route("/hosts/<int:host_id>", methods=["PUT"])
@login_required
def update_host(host_id):
    host = Host.query.get_or_404(host_id)
    data = request.get_json()
    if 'hostname' in data: host.hostname = data['hostname']
    if 'ip_address' in data: host.ip_address = data['ip_address']
    if 'os_type' in data: host.os_type = data['os_type']
    db.session.commit()
    return jsonify(host.to_dict()), 200

# --- MONITORING LIVE (GOTOWE) ---

@api_bp.route("/hosts/<int:host_id>/ssh-info", methods=["GET"])
@login_required
def get_ssh_info(host_id):
    host = Host.query.get_or_404(host_id)
    ssh_user = current_app.config.get("SSH_DEFAULT_USER", "vagrant")
    ssh_port = current_app.config.get("SSH_DEFAULT_PORT", 2222)
    ssh_key = current_app.config.get("SSH_KEY_FILE")
    try:
        with RemoteClient(host=host.ip_address, user=ssh_user, port=ssh_port, key_file=ssh_key) as remote:
            ram_out, _ = remote.run("free -m | grep Mem | awk '{print $7}'")
            disk_percentage, _ = remote.run("df -h | grep '/$' | awk '{print $5}'")
            if not disk_percentage: disk_percentage, _ = remote.run("df -h | grep '/dev/sda1' | awk '{print $5}'")
            disk_total, _ = remote.run("df -h | grep '/dev/sda1' | awk '{print $2}'")
            cpu_load, _ = remote.run("uptime | awk -F'load average:' '{ print $2 }' | cut -d',' -f1")
            uptime_seconds_str, _ = remote.run("cat /proc/uptime | awk '{print $1}'")
            uptime_formatted = "N/A"
            try:
                total_seconds = float(uptime_seconds_str)
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                uptime_formatted = f"{hours}h {minutes}m"
            except: pass

            return jsonify({
                "free_ram_mb": ram_out.strip(), "disk_info": disk_percentage.strip(),
                "disk_total": disk_total.strip(), "cpu_load": cpu_load.strip(), "uptime_hours": uptime_formatted
            }), 200
    except Exception as e:
        return jsonify({"error": f"Błąd połączenia: {str(e)}"}), 500

@api_bp.route("/hosts/<int:host_id>/windows-info", methods=["GET"])
@login_required
def get_windows_info(host_id):
    import psutil
    host = Host.query.get_or_404(host_id)
    if host.os_type != "WINDOWS": return jsonify({"error": "Wrong OS"}), 400
    try:
        mem = psutil.virtual_memory()
        free_ram_mb = str(round(mem.available / (1024 * 1024)))
        cpu_load = f"{psutil.cpu_percent(interval=0.1)}%"
        try:
            usage = psutil.disk_usage("C:\\")
            disk_percentage = f"{usage.percent}%"
            disk_total = f"{round(usage.total / (1024**3), 1)}GB"
        except:
            disk_percentage, disk_total = "N/A", "?"
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return jsonify({
            "free_ram_mb": free_ram_mb, "disk_info": disk_percentage,
            "disk_total": disk_total, "cpu_load": cpu_load, "uptime_hours": f"{hours}h {minutes}m"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================================================================
# MIEJSCE NA TWOJĄ IMPLEMENTACJĘ (ZADANIE 2 i 3)
# ===================================================================
@login_required
@api_bp.route("/hosts/<int:host_id>/logs", methods=["POST"])
def fetch_logs(host_id):
    host = Host.query.get_or_404(host_id)
    
    # Pobieramy lub tworzymy źródło logów
    log_source = LogSource.query.filter_by(host_id=host.id).first()
    if not log_source:
        log_source = LogSource(host_id=host.id, log_type='security', last_fetch=None)
        db.session.add(log_source)
        db.session.commit()
    # TODO: ZADANIE 2 - INTEGRACJA POBIERANIA LOGÓW
    # Ten endpoint obecnie nic nie robi. Twoim zadaniem jest jego uzupełnienie.
    # Wzoruj się na plikach 'test_real_ssh_logs.py' oraz 'test_windows_logs.py'.
    
    # KROKI DO WYKONANIA:
    # 1. Sprawdź host.os_type (LINUX vs WINDOWS).

    # 2. Użyj odpowiedniego klienta (RemoteClient lub WinClient).
    # 3. Wywołaj LogCollector.get_linux_logs (lub windows) aby pobrać listę zdarzeń.
    # 4. WAŻNE: Zapisz pobrane logi do pliku Parquet używając DataManager.save_logs_to_parquet().
    #    Metoda ta zwróci nazwę pliku (filename).
    # 5. Zaktualizuj log_source.last_fetch na bieżący czas.
    # 6. Dodaj wpis do LogArchive (historia pobrań).
    # 7. Wywołaj LogAnalyzer.analyze_parquet(filename, host.id) aby wykryć zagrożenia.
    
    logs = []
    try:
        # KROK 1 & 2: Wybór klienta w zależności od systemu (LINUX / WINDOWS)
        if host.os_type == "LINUX":
            # Pobieramy dane do SSH z konfiguracji aplikacji
            ssh_user = current_app.config.get("SSH_DEFAULT_USER", "vagrant")
            ssh_port = current_app.config.get("SSH_DEFAULT_PORT", 2222)
            ssh_key = current_app.config.get("SSH_KEY_FILE")

            with RemoteClient(host=host.ip_address, user=ssh_user, port=ssh_port, key_file=ssh_key) as client:
                # KROK 3: Pobranie przyrostowe (przekazujemy last_fetch)
                logs = LogCollector.get_linux_logs(client, last_fetch=log_source.last_fetch)

        elif host.os_type == "WINDOWS":
            with WinClient() as client:
                # KROK 3: Pobranie przyrostowe dla Windows
                logs = LogCollector.get_windows_logs(client, last_fetch=log_source.last_fetch)
        
        else:
            return jsonify({"error": f"Nieobsługiwany system: {host.os_type}"}), 400

        # Jeśli brak nowych logów, aktualizujemy tylko czas sprawdzenia i kończymy
        if not logs:
            log_source.last_fetch = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({"message": "Brak nowych logów", "count": 0, "alerts": 0}), 200

        # KROK 4: Zapis do pliku Parquet (Forensics)
        # To zwróci nazwę pliku, np. "host_1_20250108_120000.parquet"
        filename = DataManager.save_logs_to_parquet(logs, host.id)

        # KROK 5: Aktualizacja stanu (Timestamp)
        now = datetime.now(timezone.utc)
        log_source.last_fetch = now

        # KROK 6: Rejestracja w Archiwum (Baza SQL wie, że plik istnieje)
        new_archive = LogArchive(
            host_id=host.id,
            log_source_id=log_source.id,
            filename=filename,
            record_count=len(logs),
            timestamp=now
        )
        db.session.add(new_archive)
        db.session.commit()

        # KROK 7: Analiza Threat Intelligence (Szukanie IP z czarnej listy)
        # Funkcja analizy powinna zwrócić liczbę wykrytych alertów
        alerts_count = LogAnalyzer.analyze_parquet(filename, host.id)

        return jsonify({
            "message": "Pobrano i przeanalizowano logi",
            "count": len(logs),
            "alerts": alerts_count
        }), 200

    except Exception as e:
        # Obsługa błędów (np. host nieosiągalny)
        return jsonify({"error": f"Błąd procesu ETL: {str(e)}"}), 500

# --- REJESTR IP (Threat Intel) ---

# TODO: ZADANIE 3 - API DLA REJESTRU IP I ALERTÓW
# Poniższe endpointy są zakomentowane. Musisz je odblokować i ewentualnie uzupełnić,
# aby Panel Admina mógł zarządzać adresami IP, a Dashboard wyświetlać alerty.

# @api_bp.route("/ips", methods=["GET"])
# def get_ips():
#     ips = IPRegistry.query.order_by(IPRegistry.last_seen.desc()).all()
#     # Zwróć listę JSON
#     pass

# @api_bp.route("/ips", methods=["POST"])
# def add_ip():
#     # Dodaj nowe IP (pamiętaj o commit)
#     pass

# @api_bp.route("/ips/<int:ip_id>", methods=["PUT"])
# def update_ip(ip_id):
#     # Edycja statusu
#     pass

# @api_bp.route("/ips/<int:ip_id>", methods=["DELETE"])
# def delete_ip(ip_id):
#     # Usuwanie
#     pass

# @api_bp.route("/alerts", methods=["GET"])
# def get_recent_alerts():
#     # Zwróć 20 ostatnich alertów posortowanych malejąco po dacie
#     pass


@api_bp.route("/ips", methods=["GET"])
@login_required
def get_ips():
    # Pobieramy wszystkie IP posortowane od najnowszego
    ips = IPRegistry.query.order_by(IPRegistry.last_seen.desc()).all()
    return jsonify([ip.to_dict() for ip in ips]), 200

@api_bp.route("/ips", methods=["POST"])
@login_required
def add_ip():
    data = request.get_json()
    if not data or 'ip_address' not in data:
        return jsonify({"error": "Brak adresu IP"}), 400
    
    # Sprawdzamy czy IP już istnieje, aby uniknąć duplikatów
    if IPRegistry.query.filter_by(ip_address=data['ip_address']).first():
        return jsonify({"error": "To IP jest już w rejestrze"}), 409

    new_ip = IPRegistry(
        ip_address=data['ip_address'],
        description=data.get('description', ''),
        status=data.get('status', 'black') # Domyślnie czarna lista
    )
    db.session.add(new_ip)
    db.session.commit() # Pamiętaj o commit
    return jsonify(new_ip.to_dict()), 201

@api_bp.route("/ips/<int:ip_id>", methods=["PUT"])
@login_required
def update_ip(ip_id):
    ip_entry = IPRegistry.query.get_or_404(ip_id)
    data = request.get_json()
    
    # Pozwalamy na edycję opisu i statusu (white/black)
    if 'description' in data: ip_entry.description = data['description']
    if 'status' in data: ip_entry.status = data['status']
    
    db.session.commit()
    return jsonify(ip_entry.to_dict()), 200

@api_bp.route("/ips/<int:ip_id>", methods=["DELETE"])
@login_required
def delete_ip(ip_id):
    ip_entry = IPRegistry.query.get_or_404(ip_id)
    db.session.delete(ip_entry)
    db.session.commit()
    return jsonify({"message": "Usunięto adres IP"}), 200


# --- ALERTY (Dashboard) ---

@api_bp.route("/alerts", methods=["GET"])
@login_required
def get_recent_alerts():
    # Zwracamy 20 ostatnich alertów posortowanych malejąco po dacie
    alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(20).all()
    return jsonify([a.to_dict() for a in alerts]), 200
