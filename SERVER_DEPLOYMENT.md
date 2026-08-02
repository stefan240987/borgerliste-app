# Server-deployment (Docker)

Denne guide viser, hvordan Borgerflow køres som web-app på en server, så den kan tilgås fra mobil og desktop i browseren.

## Forudsætninger

- Docker og Docker Compose installeret på serveren
- Adgang til serverens port `8501` (eller en proxy foran)

## Installér fra GitHub (GHCR) — anbefales til Unraid

Når repoet er på GitHub, bygger Actions automatisk image:

```text
ghcr.io/<brugernavn>/borgerliste-app:latest
```

På Unraid: **Docker → Add Container** med image `ghcr.io/<brugernavn>/borgerliste-app:latest`, port `8501`, volume til `/data`.

Fuld vejledning: [README.md](README.md).

```bash
cp .env.example .env
# Sæt GHCR_IMAGE i .env
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

Gør GHCR-pakken **public** under GitHub → Packages, hvis Unraid ikke skal logge ind.

## Hurtig start (lokal build på server)

1. Kopiér hele projektmappen til serveren (eller `git clone`).
2. Opret en `.env`-fil:

```env
BORGERLISTE_ADMIN_USERNAME=admin
BORGERLISTE_ADMIN_PASSWORD=din-sikre-adgangskode
```

3. Byg og start containeren:

```bash
docker compose up -d --build
```

4. Åbn i browseren:

```text
http://<server-ip>:8501
```

## Vedvarende datalagring

Statusser gemmes i Docker-volume `borgerliste_data`, mappet til `/data` i containeren.

- Data overlever container-genstart
- For at tage backup:

```bash
docker run --rm -v borgerliste_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/borgerliste-data-backup.tar.gz -C /data .
```

## Adgangskode / GDPR

- Sæt `BORGERLISTE_ADMIN_PASSWORD` (min. 12 tegn) — påkrævet i Docker; ingen plaintext bootstrap-fil på `/data`
- Brug ikke `.streamlit/secrets.toml` i produktion; slet/rotér lokale secrets hvis de har været delt
- `BORGERLISTE_PUBLIC_SIGNUP_ENABLED=false` som standard (kan aktiveres i admin-UI)
- Kun administratorer kan slette borgerdata (Art. 17) og master-registeret
- Master-registeret er fælles for installationen — én organisation pr. deployment anbefales
- Brug HTTPS via reverse proxy (Nginx, Caddy, Traefik) i produktion
- Sæt `BORGERLISTE_COOKIE_SECURE=true` bag HTTPS
- Anbefal `BORGERLISTE_ENCRYPTION_KEY` (Fernet) i produktion og tag backup af nøglen sammen med `/data`

Unraid-skabelon: se [UNRAID_DOCKER_TEMPLATE.md](UNRAID_DOCKER_TEMPLATE.md).

## Drift

```bash
# Status
docker compose ps

# Logs
docker compose logs -f

# Stop
docker compose down

# Genstart efter opdatering
docker compose up -d --build
```

## Mobil adgang

Når serveren kører, kan du åbne samme URL på telefonen (samme netværk/VPN). Appen er optimeret til touch med store knapper og kort-layout uden horisontalt scroll.

## Lokal kørsel (Mac/PC)

De eksisterende startfiler virker stadig:

- Mac: `Start Borgerliste.command` eller `Borgerliste.app`
- Windows: `Start Borgerliste.bat`

Ved lokal kørsel uden sat adgangskode vises login-skærmen **ikke**.
