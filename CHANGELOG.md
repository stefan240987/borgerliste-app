# Changelog

Alle væsentlige ændringer til Borgerflow dokumenteres her.

Formatet er baseret på [Keep a Changelog](https://keepachangelog.com/da/1.1.0/).

## [1.5.22] — 2026-08-02 (Feedback — bugs og forbedringsforslag)

### Tilføjet

- **Feedback-side** — ny sidemenu-side hvor brugere kan indsende fejlrapporter eller forbedringsforslag (titel + beskrivelse). Tilgængelig også ved udløbet prøveperiode.
- **Admin-feedback** — ny fane under Min konto hvor administratorer kan se og filtrere indsendelser (type/bruger). Gemmes lokalt i `data/feedback.json`.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.22
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.21] — 2026-08-02 (Om Borgerflow i sidemenu)

### Ændret

- **Login** — informationsskærmen før login er fjernet; login-kortet vises direkte.
- **Sidemenu** — ny side «Om Borgerflow» med den tidligere intro-tekst (dansk/engelsk). Tilgængelig også ved udløbet prøveperiode, på linje med Privatliv.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.21
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.20] — 2026-08-02 (GDPR-fane — retention og Art. 30)

### Ændret

- **Min konto → GDPR** — tydeligere hjælpetekst for dataopbevaring; behandlingsfortegnelsen (Art. 30) viser den konfigurerede opbevaringsperiode dynamisk og præciserer, at CPR kun behandles midlertidigt i upload-sessionen. Kun tekst/UI/i18n — ingen ændring af sletnings- eller datalogik.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.20
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.19] — 2026-08-02 (Privatlivsside — letlæselig GDPR-tekst)

### Ændret

- **Privatliv og datasikkerhed** — opdateret oplysningsside med pædagogiske, audit-parate sektioner (roller, data, sikkerhed, rettigheder, brugertjekliste) på dansk og engelsk. Ingen ændring af backend, audit, upload eller eksport.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.19
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.18] — 2026-08-02 (Én ad gangen i pagination)

### Tilføjet

- **Page size** — ny mulighed for at vise én borger ad gangen (`1` / «Én ad gangen»), med tilhørende sideinfo («Borger X af Y»).

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.18
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.17] — 2026-08-02 (GDPR-flush ved idle-logout)

### Rettet

- **Idle-logout** — når session udløber pga. inaktivitet (cookie-restore fejler efter reload), flushes den aktive borgerliste nu via `logout_user` i stedet for kun at fjerne cookien. Listen genopstår dermed ikke ved næste login.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.17
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.16] — 2026-08-02 (Mobil-sidebar aria-expanded)

### Rettet

- **Mobil-sidebar** — lukket/åben detekteres via Streamlits `aria-expanded` i stedet for elementbredde (transform-skjul gav falske positives). Collapse klikker kun `stSidebarCollapseButton`, så et lukket panel ikke længere toggle-åbnes ved hvert tryk. Sidebar-JS versioneres, så stale funktioner efter deploy geninstalleres.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.16
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.15] — 2026-08-02 (GDPR-flush, mobil-sidebar og status-crash)

### Rettet

- **Mobil-sidebar** — sidebaren genåbnes ikke længere ved hvert klik; pin er desktop-only, og drawer lukkes efter navigation på små skærme.
- **GDPR ved log ud** — upload-widget, upload-signatur, Excel-cache og `status_*`-widget-state flushes sammen med den aktive liste, så filer ikke genopstår efter nyt login.
- **Zombie-upload** — tom liste + gammel fil i uploaderen tvinger ikke længere genindlæsning af GDPR-data.
- **Status / Ring igen** — selectbox undgår session-konflikter; status-handler er afskærmet, og manglende datokolonner oprettes sikkert.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.15
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.14] — 2026-07-31 (Streng single-session validering)

### Rettet

- **Sessionsstyring** — kun den senest oprettede session accepteres ved validering; ældre tokens afvises med det samme (også for sessions oprettet før 1.5.13).
- **Login-flow** — `render_login()` logger nu korrekt ud, hvis session-token er blevet overhalet af nyere login.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.14
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.13] — 2026-07-31 (Én aktiv session pr. bruger)

### Rettet

- **Sessionsstyring** — ved login invalideres eksisterende sessions for samme bruger, så samme konto ikke kan være logget ind flere steder samtidig.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.13
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.12] — 2026-07-31 (Omdøbning til Borgerflow)

### Ændret

- **App-navn** — appen hedder nu **Borgerflow** (tidligere Borgerliste) i titler, login-intro og dokumentation.
- **Fjernet produktreferencer** — alle omtaler af Nexus og DigiRehab er fjernet fra i18n-tekster og changelog.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.12
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.11] — 2026-07-31 (Responsiv sidebar CSS)

### Ændret

- **Mobil-layout CSS** — sidebar z-index, padding og fuld bredde på hovedindhold for ren visning uden overlap på små skærme.

### Rettet

- **Release-script** — `release_snapshot.sh` fejlede stille når `.cursor/rules/` manglede, så `ui/`-ændringer ikke blev med i snapshot.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.11
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.10] — 2026-07-31 (Responsiv sidebar CSS)

### Ændret

- **Mobil-layout CSS** — sidebar z-index, padding og fuld bredde på hovedindhold for ren visning uden overlap på små skærme.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.10
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.9] — 2026-07-31 (Responsiv sidebar)

### Ændret

- **Sidebar på mobil** — sidebaren starter sammenklappet på små skærme og udfoldet på desktop (`initial_sidebar_state="auto"`).
- **Mobil-layout** — CSS tilpasset sidebar z-index, padding og fuld bredde på hovedindhold for at undgå overlap.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.9
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.7] — 2026-07-31 (Min konto UI)

### Ændret

- **Min konto — visuel harmonisering** — ensartet fladt layout på tværs af alle faner (Profil, Min aktivitet, Brugere, Indstillinger, Master-register, Status-log og GDPR) med kompakte formularer, fælles tabelstil og status-badges i audit-log.
- **Brugere-fanen** — "Rediger"-knappen orddeler ikke længere; kolonnebredder og CSS tilpasset.

### Rettet

- **Rediger-bruger-dialog i mørkt tema** — modal får korrekt mørk baggrund og læsbar tekst i stedet for hvid baggrund med hvid tekst.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.7
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.6] — 2026-07-31 (Admin brugerstyring)

### Ændret

- **Admin brugerstyring** — kompakt brugertabel med badges, opret-bruger-dialog og rediger-dialog med sektioner for rolle, licens, adgangskode og deaktivering.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.6
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.5] — 2026-07-31 (Genaktiver bruger)

### Tilføjet

- **Genaktiver bruger** — administrator kan aktivere en deaktiveret konto igen under Konto → Brugere, så brugeren kan logge ind.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.5
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.4] — 2026-07-31 (Rollestyring UI)

### Rettet

- **Rollestyring UI** — dropdown og knap til at tildele/fratage admin-rettigheder under Konto → Brugere.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.4
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.3] — 2026-07-31 (Rollestyring UI)

### Rettet

- **Rollestyring UI** — dropdown til at tildele/fratage admin-rettigheder under Konto → Brugere (backend var i v1.5.2, UI manglede i deploy).

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.3
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.2] — 2026-07-31 (Admin-roller og master-sletning)

### Tilføjet

- **Rollestyring** — administratorer kan tildele og fratage admin-rettigheder for andre brugere under Konto → Brugere.

### Rettet

- **Master-sletning loggede ud** — sletning af master-register bevarer nu aktive sessioner, så administratorer forbliver logget ind.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.2
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.1] — 2026-07-31 (Personnummer i session)

### Tilføjet

- **Personnummer på borgerkort** — CPR/personnummer udtrækkes fra upload (fx `Personnummer`, `CPR`, `Cpr-nr.`) og vises midlertidigt på borgerkortet.
- **Session-only håndtering** — personnummer gemmes aldrig på disk (aktiv liste, master-register, historik, audit, Excel-eksport).

### Ændret

- **GDPR-tekst** — opdateret til at afspejle at personnummer vises i sessionen men ikke persisteres.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.1
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.5.0] — 2026-07-31 (Rapport-import, matching og borgerkort)

### Tilføjet

- **Dynamisk overskriftsdetektion** — Excel/CSV med metadata-rækker (fx `Rapport_1.xlsx`) findes automatisk via scanning af de første rækker.
- **Nye kolonne-aliaser** — `By`, `By/Adresse`, `Byen` og `Tlfnr` genkendes som Adresse/Telefonnummer.
- **Forbedret 2/3-matching** — By/adresse sammenlignes robust (postnummer, token-overlap); telefon håndterer Excel-tal.
- **Tydeligere borgerkort** — stærkere kant, skygge, spacing og status-accent i lyst og mørkt tema.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.0
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.4.1] — 2026-07-31 (Opstart rettet)

### Rettet

- **Blank/hængende side** — CookieManager fjernet (gav *unregistered ComponentInstance*); bruger `st.context.cookies` + let JS.
- **Fil-lås timeout** — `.data.lock` venter ikke længere uendeligt når zombie Streamlit-processer kører.

### Opgradering

```bash
pkill -f "streamlit run.*borgerliste"
docker compose -f docker-compose.ghcr.yml up -d --build
```

---

## [1.4.0] — 2026-07-31 (Login, signup, trial og navigation)

### Tilføjet

- **Login-introside** — informations-side før login-kortet.
- **Selvbetjent signup** — "Opret konto"-fane på login-siden med rate-limiting.
- **Trial og licens** — prøveperiode for nye brugere, admin-styring, udløbet-skærm og sidebar-badge.
- **F5-navigation** — side og konto-fane gemmes i URL (`?page=` / `?tab=`) og gendannes ved refresh.

### Bemærk

- Baseret på v1.3.0 (CookieManager og fil-lås uændret) — uden v1.5.8 opstarts-rettelser.

### Opgradering

```bash
docker compose -f docker-compose.ghcr.yml up -d --build
```

---

## [1.3.0] — 2026-07-30 (Modulær refaktor)

### Ændret

- **Modulopdeling** — monolitisk `app.py` opdelt i `config`, `i18n`, `data_io`, `storage`, `matching`, `auth` og `ui/*` for vedligeholdelse og testbarhed.
- **README** — udvidet med Docker-vejledning og funktionsbeskrivelse.
- **Dockerfile** — kopierer nye modulfiler ved build.
- **Modultest** — `test_app_modules.py` til smoke/integration-test uden Streamlit UI.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.3.0
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.2.2] — 2026-07-30 (Upload hotfix)

### Rettet

- **Fil-upload crash** — håndterer Streamlits `DeletedFile` i session state (AttributeError ved upload efter rerun/genstart).

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.2.2
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.2.1] — 2026-07-30 (Docker hotfix)

### Rettet

- **Docker/Streamlit-stabilitet** — fjernet `@st.fragment(run_every=15)` session-watchdog, som gav gentagne *fragment does not exist*-fejl og kunne genstarte containeren.
- Session udløb håndteres nu via let klient-side reload-tjek + serverside validering ved hver sidevisning.
- Fjernet overflødig `server.enableCORS=false` i Streamlit-config (konflikt med XSRF-beskyttelse).

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.2.1
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.2.0] — 2026-07-29 (GDPR)

### Tilføjet

- **Kryptering i hvile** — navn, adresse og telefon krypteres (Fernet) i JSON, Parquet og CSV.
- **Ret til sletning (Art. 17)** — slet én borger permanent fra alle lagre via borgerkort.
- **Indsigt/portabilitet (Art. 15/20)** — JSON-eksport pr. borger med alle gemte data.
- **Opbevaringsperiode** — admin konfigurerer auto-sletning af inaktive borgere (standard 24 mdr.).
- **Audit-log uden PII** — kun borger-ID; eksisterende PII migreres væk ved indlæsning.
- **Brugerdata-sletning** — admin kan slette gemte data ved deaktivering af bruger.
- **Privatlivspolitik i app** — formål, rettigheder, sikkerhed og behandlingsfortegnelse (Art. 30).
- **Min aktivitet** — alle brugere kan se egne statusændringer.

### Ændret

- Søgeforespørgsler gemmes ikke længere i session-metadata.
- Sidebar “Privatliv og datasikkerhed” udvidet med GDPR-oplysninger.
- Session-timeout konfigureres i **minutter** (`BORGERLISTE_SESSION_IDLE_MINUTES`); timer-fallback beholdes.

### Rettet

- **Fil-upload** — valg af CSV/Excel indlæser listen igen (session-watchdog og sidebar-eksport afbrød tidligere scriptet).
- **Auto-logout ved inaktivitet** — virker uden browser-genindlæsning.
- **Log ud** — sletter uploadet/gemt borgerliste for brugeren.

### Miljøvariabler

- `BORGERLISTE_ENCRYPTION_KEY` — valgfri Fernet-nøgle; oprettes automatisk i `/data` hvis tom.
- `BORGERLISTE_SESSION_IDLE_MINUTES` — erstatter `BORGERLISTE_SESSION_IDLE_HOURS` (fallback).

Docker-image:

```text
ghcr.io/stefan240987/borgerliste-app:1.2.0
ghcr.io/stefan240987/borgerliste-app:latest
```

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.2.0
docker compose -f docker-compose.ghcr.yml up -d
```

---

## [1.1.2] — 2026-07-29 (Docker hotfix + toast UI)

### Rettet

- **Docker PermissionError på `/data/.data.lock`** — entrypoint kører som root, `chown` på `/data`-volume, derefter `gosu appuser` (fixer opgradering fra root-baserede images).
- **Toast "Status gemt"** — mørkt tema + fjernelse af dobbelt-kasse omkring toast-indhold.

### Opgradering

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.1.2
docker compose -f docker-compose.ghcr.yml up -d
```

---

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
- **Non-root Docker** — container kører som `appuser` (uid 1000); entrypoint retter `/data`-volume rettigheder ved opstart.

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
