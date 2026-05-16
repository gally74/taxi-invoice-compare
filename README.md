# Taxi invoice compare

Check ABC invoice `.txt` against your Outlook **TaxiCalendar** export.

## Web app (recommended — work laptop, no install)

**https://gally74.github.io/taxi-invoice-compare/**

1. Open the link in your browser.
2. Choose your two `.txt` files.
3. Click **Compare**.
4. Download the report if you want.

Files stay **in your browser** — nothing is uploaded to GitHub when you use the webpage.

### Enable the site (once, after pushing `docs/`)

Repo → **Settings** → **Pages** → Build: **GitHub Actions** (the workflow deploys from `docs/`).

---

## Also available

- **GitHub Actions** — upload files to `inputs/` and run the workflow (see `.github/workflows/compare.yml`).
- **TaxiCompareTxt.exe** — Windows standalone app (see parent Taxi project).

---

## Privacy

- The **webpage** does not send your files to a server.
- If you use **Actions** and commit files to `inputs/`, they are stored in the repo history.
- Use a **private** repo if you use Actions with real data.

Account: **gally74**
