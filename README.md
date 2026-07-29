# Borgerliste

**Version 1.1.1** — se [CHANGELOG.md](CHANGELOG.md) for opgraderingsvejledning.

Streamlit-app til kontakt og opfølgning på borgere. Understøtter upload af Excel/CSV, statussporing, master-register med 2/3-matching, multi-bruger login, eksport og Docker-deploy.

## Funktioner

- Upload af borgerlister (Excel/CSV)
- Status: Ikke kontaktet, Accepteret, Afslået, Ring igen om 6 måneder
- Master-register der genkender borgere på tværs af lister
- Dansk/engelsk og lyst/mørkt/system-tema
- Mobilvenligt kort-layout
- Docker-image publiceres automatisk til GitHub Container Registry (GHCR)

## Lokal kørsel (Mac/PC)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Eller brug `Start Borgerliste.command` / `Start Borgerliste.bat`.

## GitHub + Docker (GHCR)

Når koden pushes til `main`, bygger GitHub Actions automatisk et Docker-image og publicerer det her:

```text
ghcr.io/<dit-brugernavn>/borgerliste-app:latest
```

### 1. Opret GitHub-repo og push

```bash
cd borgerliste-app
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/stefan240987/borgerliste-app.git
git push -u origin main
```

Gå til **Actions** på GitHub og vent til workflow **Publish Docker image** er grøn.

### 2. Gør pakken tilgængelig (vigtigt til Unraid)

For nem installation uden login:

1. GitHub → **Packages** → `borgerliste-app`
2. **Package settings** → **Change visibility** → **Public**

Alternativt: behold pakken privat og brug GitHub Personal Access Token med `read:packages` som registry-login på Unraid.

## Installér på Unraid fra GHCR

### Metode A: Unraid Docker UI (nemmest)

1. **Docker → Add Container**
2. Udfyld:

| Felt | Værdi |
|------|--------|
| Name | `borgerliste-app` |
| Repository | `ghcr.io/stefan240987/borgerliste-app:latest` |
| Network Type | `bridge` |
| Port | Host `8501` → Container `8501` |
| Path | Host `/mnt/user/appdata/borgerliste-data` → Container `/data` |
| Variable | `BORGERLISTE_DATA_DIR` = `/data` |
| Variable | `BORGERLISTE_ADMIN_PASSWORD` = stærk admin-adgangskode |

3. **Apply** og start containeren
4. Åbn `http://<unraid-ip>:8501`

Ved **privat** GHCR-pakke: tilføj **Registry URL** `ghcr.io` og login med GitHub-brugernavn + PAT.

### Metode B: SSH + Docker Compose

```bash
mkdir -p /mnt/user/appdata/borgerliste-app
cd /mnt/user/appdata/borgerliste-app

# Hent kun compose-filer (eller git clone hele repoet)
git clone https://github.com/stefan240987/borgerliste-app.git .
cp .env.example .env
# Redigér .env — sæt GHCR_IMAGE til dit image
nano .env

docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

### Opdatér til ny version

Se [CHANGELOG.md](CHANGELOG.md) for ændringer mellem versioner.

```bash
docker pull ghcr.io/stefan240987/borgerliste-app:1.1.1
# eller :latest
docker stop borgerliste-app
docker rm borgerliste-app
# Start igen via Unraid UI, eller:
docker compose -f docker-compose.ghcr.yml up -d
```

Data i volume/mappen `/mnt/user/appdata/borgerliste-data` bevares.

## Udvikling: byg lokalt

```bash
docker compose up -d --build
```

Se også [SERVER_DEPLOYMENT.md](SERVER_DEPLOYMENT.md).

## Data og sikkerhed

- Borgerdata gemmes i `/data` i containeren (Docker-volume)
- Commit **aldrig** `data/`, `.env` eller `.streamlit/secrets.toml`
- Sæt **stærk admin-adgangskode** i `.env` før produktion (`BORGERLISTE_ADMIN_PASSWORD`)
- Kun administratorer kan slette master-registeret (kræver admin-adgangskode)
- Adgangskoder skal være mindst 12 tegn; login er rate-limited efter gentagne fejl
- Session cookie holder dig logget ind ved browser-genindlæsning (standard: 24 timers inaktivitet, max 30 dage)
- Konfigurer med `BORGERLISTE_SESSION_IDLE_HOURS` og `BORGERLISTE_SESSION_MAX_DAYS` i `.env`
- Ved første lokal kørsel uden konfigureret admin-password oprettes en midlertidig adgangskode i `data/.admin_bootstrap.txt` — skift den og slet filen
- Brug HTTPS via reverse proxy (Nginx Proxy Manager, Swag) på netværk/server; eksponér ikke port 8501 direkte mod internettet

## Backup

```bash
docker run --rm -v borgerliste_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/borgerliste-data-backup.tar.gz -C /data .
```
