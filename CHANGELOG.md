# Changelog

Alle væsentlige ændringer til Borgerliste dokumenteres her.

Formatet er baseret på [Keep a Changelog](https://keepachangelog.com/da/1.1.0/).

## [1.1.1] — 2026-07-29 (stabilitet / sikkerhed / performance)

Sammenlignet med **v1.1.0**.

Docker-image:

```text
ghcr.io/stefan240987/borgerliste-app:1.1.1
ghcr.io/stefan240987/borgerliste-app:latest
```

### Tilføjet

- **Atomic JSON-skrivning** — fil-lås (`fcntl`) + temp-fil + `os.replace` for alle JSON-datafiler.
- **Master-sync throttling** — fuld sync fra alle brugere køres max hver 60 sekund (ikke ved hvert page view).
- **Batch status-gem** — én låst transaktion for liste, master, history og audit ved statusændring.
- **Excel upload-grænse** — samme 25 MB grænse som CSV (læser bytes før parsing).
- **Secure session cookie** — `BORGERLISTE_COOKIE_SECURE=true` i produktion bag HTTPS.
- **Proxy-aware rate limit** — `X-Forwarded-For` bruges kun når `BORGERLISTE_TRUST_PROXY=true`.
- **Non-root Docker** — container kører som `appuser` (uid 1000).

### Ændret

- `sync_session_df_with_master()` kalder throttlet sync i stedet for fuld sync hver gang.
- Fuld master-sync tvinges ved login-gendannelse, upload og admin master-panel.

### Rettet

- Race conditions ved samtidige JSON-skrivninger mellem brugere.
- Excel-filer kunne omgå upload-størrelsesgrænse.
- Unødvendig disk- og CPU-belastning ved hver sideindlæsning.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.1.1
# Tilføj i .env bag HTTPS:
# BORGERLISTE_COOKIE_SECURE=true
# BORGERLISTE_TRUST_PROXY=true   # kun bag reverse proxy
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.1.0] — 2026-07-29 (Docker / GHCR)

Sammenlignet med **v1.0.x** (seneste: commit `701f333` — tema-rettelser i Docker, ingen login).

Docker-image:

```text
ghcr.io/stefan240987/borgerliste-app:1.1.0
ghcr.io/stefan240987/borgerliste-app:latest
```

### Tilføjet

- **Login og brugerkonti** — adskilte brugere med roller (`admin` / `user`); adgangskoder hashes med bcrypt.
- **Persistent session** — cookie-baseret login overlever browser-genindlæsning; konfigurerbar inaktiv timeout og max levetid via miljøvariabler.
- **Admin-panel under Min konto** — opret brugere, administrer roller, og konfigurer session-timeout (1–168 timer) gemt i `data/app_settings.json`.
- **Per-bruger datalagring** — hver bruger får egen mappe under `data/user_data/<brugernavn>/` med aktiv liste, præferencer og session-metadata.
- **Automatisk gendannelse af åben liste** — ved login/refresh indlæses sidste aktive borgerliste fra Parquet/CSV + session-metadata.
- **Status-log (audit)** — alle statusændringer logges med bruger, tidspunkt og borger; admin kan filtrere i Min konto.
- **Master-register sync på tværs af brugere** — fælles statusregister opdateres fra alle brugeres gemte lister ved hver session.
- **Sidebar UX** — menu collapsed som standard, auto-luk efter 10 sekunder, og pin-knap ved sidebar-toggle for at fastholde menuen.
- **Rate limiting på login** — midlertidig lockout efter gentagne fejlede loginforsøg.
- **Sikkerhedsforbedringer** — inputvalidering, XSS-sikring i HTML-eksport, uploadstørrelsesgrænse, sikre filstier.
- **Logo og assets** — SVG-logo inkluderet i Docker-image (`assets/borgerliste-logo.svg`).
- **Ny afhængighed** — `extra-streamlit-components` til cookie-håndtering.

### Ændret

- **Docker miljøvariabler** — `BORGERLISTE_MASTER_DELETE_PASSWORD` er erstattet af:
  - `BORGERLISTE_ADMIN_USERNAME` (påkrævet)
  - `BORGERLISTE_ADMIN_PASSWORD` (påkrævet, min. 12 tegn anbefales)
  - `BORGERLISTE_SESSION_IDLE_HOURS` (standard: 24)
  - `BORGERLISTE_SESSION_MAX_DAYS` (standard: 30)
- **Status-gemning** — bruger `on_change`-callback i stedet for inline sammenligning ved hver render (forhindrer toast-/genindlæsnings-loop).
- **Master-register upsert** — respekterer nyeste `Status dato` / `updated_at`; status-only JSON-filer uden navn/adresse synces ikke længere til master.
- **Master-register oprydning** — ugyldige og duplikerede poster fjernes automatisk ved indlæsning.
- **Sidebar styling** — strammere navigation, bruger-pill, og diskret indstillingspanel.
- **Dokumentation** — README og SERVER_DEPLOYMENT opdateret til ny auth-model og Unraid/GHCR-flow.

### Rettet

- **Login brudt** — `CookieManager` brugte samme session state-nøgle som widget → `StreamlitAPIException`; adskilt instans-nøgle.
- **Logout KeyError** — sikker sletning af auth-cookie ved logud.
- **Pin-knap synlig i sidebar** — skjult bridge-knap via `st-key-*` CSS; pin-ikon placeres ved sidebar-toggle.
- **Status “Status gemt” loop** — gentagen toast og rerun ved statusændring.
- **Master-register voksede med tomme poster** — hundredvis af dubletter fra status-only JSON uden borgeridentitet.
- **Browser refresh mistede åben fil** — `restore_active_list_if_available()` manglede kald efter login.

### Sikkerhed / migration fra v1.0.x

1. Opret `.env` ud fra `.env.example` med **stærk admin-adgangskode** før opstart.
2. Eksisterende data i Docker-volume `/data` bevares — migrering sker automatisk ved første login.
3. Fjern eventuelle gamle referencer til `BORGERLISTE_MASTER_DELETE_PASSWORD` i Unraid/Compose.
4. Eksponér ikke port 8501 direkte mod internettet; brug HTTPS reverse proxy.

### Opgradering (Docker)

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.1.0
# Opdatér .env med BORGERLISTE_ADMIN_USERNAME og BORGERLISTE_ADMIN_PASSWORD
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.0.x] — 2026 (tema / Docker-baseline)

- Initial Docker + GHCR workflow (`20e474a`)
- GHCR URL rettet til `stefan240987` (`419ba0d`)
- Tema-rendering i Docker uden JavaScript (`7ead926`, `4d5a35e`, `d07e29b`, `701f333`)
- Enkeltbruger-app uden login; master-sletning via `BORGERLISTE_MASTER_DELETE_PASSWORD`
