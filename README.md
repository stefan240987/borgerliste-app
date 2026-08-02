# Borgerflow

**Version 1.5.29** — se [CHANGELOG.md](CHANGELOG.md) for ændringer og opgradering.

Borgerflow er en webapp til **kontakt og opfølgning på borgere**. Den er målrettet teams, der arbejder med borgerlister — fx outreach, tilbud, opfølgning på henvendelser eller koordinering af telefon-/besøgskontakt.

Upload en Excel- eller CSV-liste, følg status pr. borger, og genkend samme person automatisk på tværs af nye lister via et master-register.

## Hvad bruges appen til?

- **Importere borgerlister** — Excel (`.xlsx`) og CSV med navn, by/adresse og telefon
- **Sætte og følge status** — fx *Ikke kontaktet endnu*, *Accepteret tilbud*, *Afslået*, *Ring igen om 6 måneder*
- **Holde styr på kontakthistorik** — status gemmes og genkendes, selv når du uploader en ny liste
- **Filtrere på indsats** — når listen har `Indsats navn`, kan du filtrere borgere og KPI-tal pr. indsats
- **Arbejde flere sammen** — login med roller (admin/bruger), hver bruger kan have egne lister
- **Eksportere og dokumentere** — CSV/Excel-eksport, feedback og GDPR-værktøjer (sletning, indsigt, audit-log)

Appen kører i browseren (desktop og mobil) og er bygget med Python/Streamlit.

## Funktioner

- Upload af borgerlister (Excel/CSV)
- Master-register med 2/3-matching på tværs af lister
- Statussporing med historik og KPI-overblik
- Indsats-filter (når kolonnen findes) — KPI følger det valgte filter
- Session-only felter: personnummer og indsats navn vises midlertidigt, gemmes ikke
- Feedback: brugere kan indsende fejl/forslag; admin styrer status (åben/lukket/implementeret/afvist)
- Sider: Borgerliste, Min konto, Privatliv, Om, Feedback
- Dansk/engelsk og lyst/mørkt/system-tema
- Mobilvenligt kort-layout
- Kryptering af persondata (navn, adresse/by, telefon) i hvile
- Multi-bruger login med session-cookie og rate-limited login (IP + brugernavn)
- Valgfri prøveperiode pr. bruger (styres af admin)
- Docker-image publiceres automatisk til GitHub Container Registry (GHCR)

---

## Installér med Docker (anbefalet)

Det nemmeste er at køre det færdigbyggede image fra GHCR. Data gemmes i et Docker-volume, så opdateringer bevarer dine lister og statusser.

**Image:**

```text
ghcr.io/stefan240987/borgerliste-app:latest
```

Tagget version (fx `1.5.29`) kan bruges i stedet for `latest`, hvis du vil låse til en bestemt udgave.

### Krav

- Docker og Docker Compose
- Port **8501** tilgængelig på værten (eller brug reverse proxy — se [Data og sikkerhed](#data-og-sikkerhed))

### Trin 1: Hent compose-filer

```bash
git clone https://github.com/stefan240987/borgerliste-app.git
cd borgerliste-app
cp .env.example .env
```

### Trin 2: Konfigurér `.env`

Redigér `.env` og sæt mindst admin-bruger og adgangskode:

```env
GHCR_IMAGE=ghcr.io/stefan240987/borgerliste-app:latest
BORGERLISTE_ADMIN_USERNAME=admin
BORGERLISTE_ADMIN_PASSWORD=din-staerke-adgangskode-her
```

Adgangskoden skal være mindst 12 tegn. Brug en stærk, unik adgangskode i produktion.

I Docker kræves admin-password ved første start (ingen plaintext bootstrap-fil i `/data`).

### Trin 3: Start containeren

```bash
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

### Trin 4: Åbn appen

```text
http://<server-ip>:8501
```

Log ind med brugernavnet og adgangskoden fra `.env`.

### Opdatér til ny version

```bash
# Seneste (hvis GHCR_IMAGE peget på :latest)
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d

# Eller lås til en bestemt version i .env, fx:
# GHCR_IMAGE=ghcr.io/stefan240987/borgerliste-app:1.5.29
```

Data i volume `borgerliste_data` bevares ved opdatering. Se [CHANGELOG.md](CHANGELOG.md) for detaljer mellem versioner.

### Alternativ: `docker run` (uden Compose)

Hvis du foretrækker én kommando uden compose-filer:

```bash
docker run -d \
  --name borgerliste-app \
  --restart unless-stopped \
  -p 8501:8501 \
  -e BORGERLISTE_DATA_DIR=/data \
  -e BORGERLISTE_ADMIN_USERNAME=admin \
  -e BORGERLISTE_ADMIN_PASSWORD=din-staerke-adgangskode-her \
  -v borgerliste_data:/data \
  ghcr.io/stefan240987/borgerliste-app:1.5.29
```

---

## Installér på Unraid

Se den fulde trin-for-trin guide: [UNRAID_DOCKER_TEMPLATE.md](UNRAID_DOCKER_TEMPLATE.md) (skabelon, miljøvariabler, volume og opgradering uden datatab).

### Hurtig Docker UI

1. **Docker → Add Container**
2. Udfyld:

| Felt | Værdi |
|------|--------|
| Name | `borgerliste-app` |
| Repository | `ghcr.io/stefan240987/borgerliste-app:1.5.29` (eller `:latest`) |
| Network Type | `bridge` |
| Port | Host `8501` → Container `8501` (TCP) |
| Path | Host `/mnt/user/appdata/borgerliste-data` → Container `/data` |
| Variable | `BORGERLISTE_DATA_DIR` = `/data` |
| Variable | `BORGERLISTE_ADMIN_USERNAME` = `admin` |
| Variable | `BORGERLISTE_ADMIN_PASSWORD` = stærk adgangskode (min. 12 tegn) |
| Variable | `BORGERLISTE_PUBLIC_SIGNUP_ENABLED` = `false` |
| Variable | `BORGERLISTE_COOKIE_SECURE` = `true` (kun bag HTTPS) |

3. **Apply** og start containeren
4. Åbn `http://<unraid-ip>:8501` (eller via reverse proxy)

### GHCR-adgang

Gør pakken **public** under GitHub → **Packages** → `borgerliste-app` → **Package settings**, så Unraid kan hente image uden login.

Alternativt: behold pakken privat og log ind med GitHub-brugernavn + Personal Access Token (`read:packages`) som registry-login.

---

## Lokal kørsel uden Docker (udvikling)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Eller brug `Start Borgerliste.command` / `Start Borgerliste.bat`.

Byg lokalt med Docker:

```bash
cp .env.example .env
docker compose up -d --build
```

Se [SERVER_DEPLOYMENT.md](SERVER_DEPLOYMENT.md) for mere om server-deploy og reverse proxy.

---

## Data og sikkerhed

- Borgerdata gemmes i `/data` i containeren (Docker-volume `borgerliste_data`)
- Persondata (navn, adresse/by, telefon) krypteres i hvile
- **Master-registeret er fælles** for hele installationen (status genkendes på tværs af brugere). Anbefaling: én organisation pr. installation; overvej DPIA hvis flere teams deler samme app
- CPR/personnummer og indsats navn kan vises i aktiv session, men **gemmes ikke** og flushes ved logud/timeout
- Commit **aldrig** `data/`, `.env` eller `.streamlit/secrets.toml` (brug heller ikke `secrets.toml` i produktion — brug env-variabler)
- Sæt **stærk admin-adgangskode** i `.env` / Unraid før produktion (påkrævet i Docker)
- Selvbetjent signup er **slået fra** som standard (`BORGERLISTE_PUBLIC_SIGNUP_ENABLED=false`)
- Kun administratorer kan slette borgerdata (Art. 17) og master-registeret; sletning kræver 3/3-match (eller eksakt citizen-id)
- Audit-log dækker også eksport, sletning, login, signup, admin-handlinger og master-wipe (uden PII)
- Login er rate-limited (IP + brugernavn) efter gentagne fejl
- Session cookie holder dig logget ind ved browser-genindlæsning (standard: 24 timers inaktivitet, max 30 dage)
- Konfigurer med `BORGERLISTE_SESSION_IDLE_MINUTES` og `BORGERLISTE_SESSION_MAX_DAYS` i `.env`
- Bag HTTPS reverse proxy: sæt `BORGERLISTE_COOKIE_SECURE=true` i `.env`; sæt kun `BORGERLISTE_TRUST_PROXY=true` bag en trusted proxy
- Anbefal `BORGERLISTE_ENCRYPTION_KEY` i produktion (ellers auto-nøgle i `/data`)
- Eksponér ikke port 8501 direkte mod internettet — brug Nginx Proxy Manager, Swag, Caddy eller tilsvarende

## Backup

```bash
docker run --rm -v borgerliste_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/borgerliste-data-backup.tar.gz -C /data .
```

## Udvikling og CI

Ved push til `main` bygger GitHub Actions automatisk og publicerer image til GHCR. Workflow: **Publish Docker image**.
