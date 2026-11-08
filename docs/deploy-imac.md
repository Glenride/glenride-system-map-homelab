# Deploy: Glenride System Map on the iMac

Get the interactive system map running on your iMac in Docker. Follow top to
bottom. Every command is meant to be copied and run exactly as written.

> **Example values below are marked EXAMPLE.** Where you see one, use your own
> real value instead — your iMac's username and its address on your home
> network. Everything else, run as-is.

---

## 1. Install Docker on the iMac

Open a terminal on the iMac and run:

```bash
omarchy-pkg-add docker docker-compose
```

Start Docker and make it start on every boot:

```bash
sudo systemctl enable --now docker
```

Give your own user permission to run Docker (avoids typing `sudo` forever):

```bash
sudo usermod -aG docker $USER
```

**Log out of the iMac and log back in** so the new permission takes effect.
(Or reboot — same result.)

Check it worked:

```bash
docker --version
docker compose version
```

You should see version numbers for both, with no "permission denied".

---

## 2. Find your iMac's address on your home network

```bash
ip -4 addr show | grep inet
```

Look for the line starting with `inet 192.168.` or `inet 10.` — for example
`inet 192.168.1.50/24`. The address before the `/` is your iMac's LAN address.
Write it down; you need it in steps 3 and 5.

*(EXAMPLE below: `192.168.1.50` and username `housedv` stand in for your real
values.)*

---

## 3. Copy the project folder to the iMac

From the computer where the project folder lives, run:

```bash
scp -r ~/workspace/your_files/glenride-system-map-homelab housedv@192.168.1.50:~/projects/
```

What this does: copies the whole folder into a `projects` directory in your
iMac home folder. Replace `housedv` with your iMac username and `192.168.1.50`
with the address from step 2. It will ask for your iMac password.

---

## 4. Start it

On the iMac:

```bash
cd ~/projects/glenride-system-map-homelab
docker compose up -d --build
```

Wait about a minute for the first build. Then check it's running:

```bash
docker compose ps
```

You should see `glenride-system-map` with state `Up`.

---

## 5. Open it

On any device on your home network (your phone, the iMac browser), open:

```
http://192.168.1.50:8090
```

(Using your iMac's real address from step 2.) You should see the Glenride
System Map with the camel logo. Click any card, then **Edit** — type, hit
**Save**, and reload the page to confirm your edit stuck.

---

## 6. View the logs (if something looks wrong)

```bash
cd ~/projects/glenride-system-map-homelab
docker compose logs -f
```

Press `Ctrl+C` to stop watching. The last lines usually say what went wrong.

---

## 7. Update it later

After changing files (or receiving an updated folder), copy the new files over
and rebuild:

```bash
scp -r ~/workspace/your_files/glenride-system-map-homelab housedv@192.168.1.50:~/projects/
```

Then on the iMac:

```bash
cd ~/projects/glenride-system-map-homelab
docker compose up -d --build
```

Your card edits are safe: they live in a Docker volume, not in the rebuilt
image.

---

## 8. Back up your edits

Your card edits live in one SQLite file inside the `glenride-map-data` Docker
volume. Back it up like this:

```bash
mkdir -p ~/map-backups
docker run --rm -v glenride-map-data:/data -v ~/map-backups:/backup alpine tar czf /backup/system-map-backup.tar.gz -C /data system-map.db
ls -la ~/map-backups/
```

Run that whenever you've made edits you don't want to lose. To restore, stop
the app first, then unpack a backup into the volume:

```bash
cd ~/projects/glenride-system-map-homelab
docker compose stop
docker run --rm -v glenride-map-data:/data -v ~/map-backups:/backup alpine tar xzf /backup/system-map-backup.tar.gz -C /data
docker compose start
```

---

## 9. Stop and start

```bash
cd ~/projects/glenride-system-map-homelab
docker compose stop    # stop it (edits are kept)
docker compose start   # start it again
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `permission denied` on any docker command | You skipped the logout/login after `usermod`. Log out and back in, then retry. |
| `port is already allocated` / `address already in use` | Something else uses port 8090. In `docker-compose.yml`, change `"8090:8000"` to `"8091:8000"`, then `docker compose up -d --build` and open port 8091. |
| Page won't load from your phone | Phone must be on the same Wi-Fi as the iMac. Double-check the address from step 2. |
| `docker compose` says "command not found" | Run step 1 again; the `docker-compose` package provides the plugin. |
| Build fails on `pip install` | Check the logs (step 6) — usually a network hiccup; rerun `docker compose up -d --build`. |

---

## Optional: reach it from outside your home

By default this runs on your home network only — no accounts, no tunnel, no
exposure. If you later want to open it from anywhere, the same Cloudflare
Tunnel setup used for your other iMac services works: point a tunnel hostname
at `http://localhost:8090`. Not required for normal use.
