/**
 * Wrapper na Fetch API do komunikacji z backendem Flask
 */

// --- HOSTS (GOTOWE - WZÓR) ---
export async function fetchHosts() {
    const res = await fetch('/api/hosts');
    return await res.json();
}
export async function createHost(data) {
    const res = await fetch('/api/hosts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if(!res.ok) throw new Error((await res.json()).error);
    return await res.json();
}
export async function updateHost(id, data) {
    const res = await fetch(`/api/hosts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if(!res.ok) throw new Error('Błąd edycji hosta');
    return await res.json();
}
export async function removeHost(id) {
    await fetch(`/api/hosts/${id}`, { method: 'DELETE' });
}

// --- MONITORING / LOGI (GOTOWE) ---
export async function checkHostStatus(id, osType) {
    const endpoint = (osType === 'LINUX') 
        ? `/api/hosts/${id}/ssh-info` 
        : `/api/hosts/${id}/windows-info`;
        
    const res = await fetch(endpoint);
    if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || `Błąd HTTP ${res.status}`);
    }
    return await res.json();
}

export async function triggerLogFetch(hostId) {
    const res = await fetch(`/api/hosts/${hostId}/logs`, {
        method: 'POST'
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Błąd pobierania logów');
    }
    return await res.json();
}

// ===============================================================
// TODO: ZADANIE 4 - KOMUNIKACJA FRONTEND-BACKEND
// ===============================================================
// Brakuje funkcji do obsługi Rejestru IP oraz Alertów.
// Panel Admina i Dashboard będą rzucać błędy, dopóki tego nie uzupełnisz.
// Wzoruj się na funkcjach z sekcji HOSTS powyżej.

/*
export async function fetchIPs() {
    // 1. Wykonaj fetch GET na '/api/ips'
    // 2. Zwróć json
}

export async function createIP(data) {
    // 1. Wykonaj fetch POST na '/api/ips' z danymi (body)
    // 2. Obsłuż błędy (!res.ok)
}

export async function updateIP(id, data) {
    // PUT na /api/ips/<id>
}

export async function removeIP(id) {
    // DELETE na /api/ips/<id>
}

export async function fetchAlerts() {
    // GET na /api/alerts
}
*/

// 1. Pobieranie listy IP (do tabeli w panelu admina)
export async function fetchIPs() {
    const res = await fetch('/api/ips');
    if (!res.ok) throw new Error('Błąd pobierania listy IP');
    return await res.json();
}

// 2. Dodawanie nowego IP (do Czarnej/Białej listy)
export async function createIP(data) {
    const res = await fetch('/api/ips', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    // Ważne: Backend może zwrócić błąd 409 (Duplikat IP), musimy go odczytać
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Błąd dodawania IP');
    }
    return await res.json();
}

// 3. Edycja IP (np. zmiana statusu z BANNED na TRUSTED)
export async function updateIP(id, data) {
    const res = await fetch(`/api/ips/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Błąd aktualizacji IP');
    return await res.json();
}

// 4. Usuwanie IP z rejestru
export async function removeIP(id) {
    const res = await fetch(`/api/ips/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Błąd usuwania IP');
}

// 5. Pobieranie Alertów (Kluczowe dla Dashboardu!)
export async function fetchAlerts() {
    const res = await fetch('/api/alerts');
    if (!res.ok) throw new Error('Błąd pobierania alertów');
    return await res.json();
}