# Unraid: ny Docker-skabelon til Borgerflow

Denne guide opretter en **ny** Unraid Docker-skabelon til Borgerflow (fra version **1.5.29**), så appen starter korrekt med krævet admin-adgangskode, lukket signup og vedvarende data.

## Forudsætninger

- Unraid med Docker aktiveret
- Adgang til GHCR-image: `ghcr.io/stefan240987/borgerliste-app`
- Pakken bør være **public** (ellers registry-login med GitHub PAT med `read:packages`)

## Trin 1 — Opret datamappe

I Unraid terminal eller File Manager:

```bash
mkdir -p /mnt/user/appdata/borgerliste-data
chown -R 1000:1000 /mnt/user/appdata/borgerliste-data
```

Appen kører typisk som UID 1000 i containeren. Forkert ejerskab giver skrivefejl til `/data`.

## Trin 2 — Add Container (ny skabelon)

1. Gå til **Docker** → **Add Container**
2. Hvis du har en gammel skabelon: klik **Remove** på den gamle container først (volume/data bevares, hvis path er den samme), eller opret en ny med andet navn midlertidigt
3. Udfyld felterne nedenfor
4. Klik **Apply**

### Basis

| Felt | Værdi |
|------|--------|
| Name | `borgerliste-app` |
| Repository | `ghcr.io/stefan240987/borgerliste-app:1.5.29` |
| Registry URL | (tom hvis public) |
| Network Type | `Bridge` |
| Console shell command | `Bash` (valgfrit) |
| Privileged | **Off** |

Brug tag `1.5.29` til kontrolleret opgradering. `:latest` kan bruges, når du bevidst vil følge nyeste release.

### Port

| Host Port | Container Port | Type |
|-----------|----------------|------|
| `8501` | `8501` | TCP |

Hvis porten er optaget, vælg en ledig host-port (fx `8502`) og husk den i browser-URL’en.

### Volume / Path

| Config Type | Name | Container Path | Host Path | Access Mode |
|-------------|------|----------------|-----------|-------------|
| Path | `data` | `/data` | `/mnt/user/appdata/borgerliste-data` | Read/Write |

**Vigtigt:** Genbrug samme host-path ved opgradering, ellers mister du brugere, lister og master-register.

### Environment variables

Tilføj disse som **Variable** (ikke bare i Extra Parameters, medmindre du foretrækker det):

| Name | Value | Påkrævet |
|------|--------|----------|
| `BORGERLISTE_DATA_DIR` | `/data` | Ja |
| `BORGERLISTE_ADMIN_USERNAME` | `admin` | Ja (første start) |
| `BORGERLISTE_ADMIN_PASSWORD` | *stærk unik adgangskode, min. 12 tegn* | **Ja** |
| `BORGERLISTE_PUBLIC_SIGNUP_ENABLED` | `false` | Anbefalet |
| `BORGERLISTE_COOKIE_SECURE` | `false` | `true` hvis bag HTTPS-proxy |
| `BORGERLISTE_TRUST_PROXY` | `false` | `true` kun bag trusted reverse proxy |
| `BORGERLISTE_SESSION_IDLE_MINUTES` | `1440` | Valgfri |
| `BORGERLISTE_SESSION_MAX_DAYS` | `30` | Valgfri |
| `BORGERLISTE_ENCRYPTION_KEY` | Fernet-nøgle (base64) | Anbefalet i produktion |
| `BORGERLISTE_REQUIRE_ADMIN_PASSWORD` | `true` | Valgfri (default true når data-dir er `/data`) |

#### Generér krypteringsnøgle (valgfrit men anbefalet)

```bash
docker run --rm python:3.12-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Gem værdien som `BORGERLISTE_ENCRYPTION_KEY`. **Mistet nøgle = data kan ikke dekrypteres.** Tag backup af nøglen sammen med appdata.

## Trin 3 — Start og log ind

1. Start containeren
2. Åbn logs: **Docker → borgerliste-app → Logs** — den bør lytte på port 8501
3. Åbn `http://<unraid-ip>:8501`
4. Log ind med `BORGERLISTE_ADMIN_USERNAME` / `BORGERLISTE_ADMIN_PASSWORD`

Hvis appen siger, at admin-password mangler: sæt `BORGERLISTE_ADMIN_PASSWORD`, **Apply**, og genstart containeren.

## Trin 4 — Gem som skabelon (valgfrit)

Efter en fungerende container:

1. I Docker UI: brug Unraids mulighed for at **gemme template** / redigér XML under `flash/config/plugins/dockerMan/templates-user/`
2. Eller behold container-konfigurationen og opdatér kun **Repository**-tag ved næste release

## Opgradering fra ældre version (bevar data)

1. Notér nuværende host-path til `/data` (fx `/mnt/user/appdata/borgerliste-data`)
2. Stop den gamle container
3. Ændr **Repository** til `ghcr.io/stefan240987/borgerliste-app:1.5.29`
4. Tilføj manglende env-variabler fra tabellen ovenfor (især admin-password og `PUBLIC_SIGNUP_ENABLED=false`)
5. Behold **samme** path-mapping til `/data`
6. **Apply** / start
7. Log ind og kontrollér, at borgerlister og master-register stadig er der

### Opgradering via compose på Unraid (alternativ)

Hvis du kører via compose i en share:

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.5.29
# Opdatér GHCR_IMAGE / tag i din compose/.env
docker compose -f docker-compose.ghcr.yml up -d
```

## Reverse proxy (anbefalet til HTTPS)

Bag Nginx Proxy Manager, Swag eller Caddy foran containeren:

1. Proxy host → `http://borgerliste-app:8501` (eller host-IP + port)
2. Aktivér SSL
3. Sæt i containeren: `BORGERLISTE_COOKIE_SECURE=true`
4. Hvis proxy sætter `X-Forwarded-For`: `BORGERLISTE_TRUST_PROXY=true` (kun hvis proxyen er trusted og overskriver headeren)

Eksponér ikke port 8501 direkte mod internettet.

## Fejlfinding

| Symptom | Tjek |
|---------|------|
| Container genstarter / kan ikke oprette admin | `BORGERLISTE_ADMIN_PASSWORD` sat og ≥ 12 tegn? |
| Permission denied på `/data` | `chown -R 1000:1000` på host-path |
| Tom app efter opgradering | Forkert host-path — genbrug tidligere appdata-mappe |
| Kan ikke pulle image | Pakke public? Eller GitHub login + PAT `read:packages` |
| Cookie/session problemer bag HTTPS | `BORGERLISTE_COOKIE_SECURE=true` |
| Signup synlig uønsket | `BORGERLISTE_PUBLIC_SIGNUP_ENABLED=false` eller slå fra under Min konto → Indstillinger |

## Sikkerhed ved Unraid-drift

- Del ikke admin-password i screenshots eller delte templates
- Brug unik, stærk `BORGERLISTE_ADMIN_PASSWORD`
- Hold signup slået fra, medmindre I bevidst vil have selvbetjening
- Tag regelmæssig backup af `/mnt/user/appdata/borgerliste-data` **og** encryption key
- Master-registeret er fælles for alle brugere i denne installation
