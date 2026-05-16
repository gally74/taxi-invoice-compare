# Taxi invoice compare (GitHub)

Check ABC invoice `.txt` against your Outlook **TaxiCalendar** export — in the cloud, no `.exe` on your work PC.

Same logic as `TaxiCompareTxt.exe` on your home machine.

**Use a private repository** — invoice and driver names are sensitive.

Account: **gally74** (same as [weekly-circular-processor](https://github.com/gally74/weekly-circular-processor))

---

## Each month (browser only — work laptop OK)

1. Open your repo on GitHub (e.g. `gally74/taxi-invoice-compare`).
2. Go to folder **`inputs/`** → **Add file** → **Upload files**.
3. Upload **one** `TaxiCalendar....txt` and **one** `ABC_Invoice....txt`.  
   Remove/replace any older `.txt` files in `inputs/` first.
4. **Commit** the upload.
5. Open **Actions** → workflow **Compare invoice vs calendar** → **Run workflow** → **Run workflow**.  
   (It also runs automatically when you change files in `inputs/`.)
6. When the run is green, open the run → **Artifacts** → download **`TaxiCompare_Result`**.

The report lists invoice trips **not** found in your calendar export.

---

## First-time setup (once, home PC)

### 1. Create a new **private** repo on GitHub

- Click **New** on https://github.com/gally74  
- Name: `taxi-invoice-compare`  
- **Private**  
- Do not add a README (this folder already has one)

### 2. Push this folder to GitHub

In PowerShell (folder = this `taxi-invoice-compare` directory):

```powershell
cd "C:\Users\Roy\OneDrive - IR\Cursor Projects\Taxi\taxi-invoice-compare"
git init
git add .
git commit -m "Taxi invoice compare for GitHub Actions"
git branch -M main
git remote add origin https://github.com/gally74/taxi-invoice-compare.git
git push -u origin main
```

(Use GitHub Desktop instead if you prefer.)

### 3. Enable Actions

Repo → **Settings** → **Actions** → **General** → allow actions.

---

## Folder layout

```
taxi-invoice-compare/
  compare_taxi_txt.py      # compare script
  inputs/                  # you upload .txt files here
  output/                  # report written here in CI (artifact download)
  .github/workflows/       # automation
```

---

## Privacy

- **Private repo** strongly recommended.  
- Uploaded files stay in git history until you delete them — remove old months from `inputs/` when done.  
- GitHub Actions runs on Microsoft-hosted runners; do not use if your employer forbids cloud processing of this data.
