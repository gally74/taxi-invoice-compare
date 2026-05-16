/** Taxi invoice vs calendar compare — runs entirely in your browser (no upload). */

const MONTHS = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
  jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
};

const INV_LINE = new RegExp(
  "^[^\\S\\r\\n]*(?:Date\\s+)?(\\d{1,2}-[A-Za-z]{3}-\\d{2})\\s+(?:Time\\s+)?(\\d{1,2}:\\d{2})\\b.*?" +
    "IRISH\\s+RAIL\\s*-\\s*(.+?)(?:\\s+From:|\\s+€\\s*\\d|\\s+\\u20ac\\s*\\d|\\s*$)",
  "gim"
);

const CAL_BLOCK = new RegExp(
  "#(\\d+)\\s*" +
    "Date\\s*:\\s*([^\\n]+)\\s*" +
    "Time\\s*:\\s*([^\\n]+)\\s*" +
    "Driver\\s*:\\s*([^\\n]+)\\s*" +
    "Route\\s*:\\s*([^\\n]+)",
  "gis"
);

function normDriver(name) {
  return name.trim().toUpperCase().replace(/'/g, " ").replace(/\s+/g, " ").trim();
}

function parseHhmm(s) {
  const [a, b] = s.trim().split(":");
  return `${String(parseInt(a, 10)).padStart(2, "0")}:${String(parseInt(b, 10)).padStart(2, "0")}`;
}

function ymdFromDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

function parseInvoiceDate(raw) {
  const m = raw.trim().match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2})$/);
  if (!m) return null;
  const mon = MONTHS[m[2].toLowerCase()];
  if (mon === undefined) return null;
  let year = parseInt(m[3], 10);
  year += year < 70 ? 2000 : 1900;
  return new Date(year, mon, parseInt(m[1], 10));
}

function parseCalendarDate(line) {
  line = line.trim();
  let d = new Date(line);
  if (!isNaN(d.getTime())) return d;
  const m = line.match(/(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (!m) return null;
  d = new Date(`${m[2]} ${m[1]}, ${m[3]}`);
  return isNaN(d.getTime()) ? null : d;
}

function parseInvoiceText(text) {
  const out = [];
  let m;
  INV_LINE.lastIndex = 0;
  while ((m = INV_LINE.exec(text)) !== null) {
    let drv = m[3].trim();
    if (!drv || /^details$/i.test(drv)) continue;
    const dt = parseInvoiceDate(m[1]);
    if (!dt) continue;
    const ymd = ymdFromDate(dt);
    const hhmm = parseHhmm(m[2]);
    const nd = normDriver(drv);
    const snippet = m[0].replace(/\s+/g, " ").trim().slice(0, 160);
    out.push({ key: `${ymd}|${hhmm}|${nd}`, ymd, hhmm, driver: nd, detail: snippet });
  }
  return out;
}

function parseCalendarText(text) {
  const out = [];
  let m;
  CAL_BLOCK.lastIndex = 0;
  while ((m = CAL_BLOCK.exec(text)) !== null) {
    const dt = parseCalendarDate(m[2]);
    if (!dt) continue;
    let hhmm;
    try {
      hhmm = parseHhmm(m[3]);
    } catch {
      continue;
    }
    const ymd = ymdFromDate(dt);
    const nd = normDriver(m[4]);
    out.push({
      key: `${ymd}|${hhmm}|${nd}`,
      ymd,
      hhmm,
      driver: nd,
      detail: `#${m[1]}  ${m[5].trim()}`,
    });
  }
  return out;
}

function multisetMatch(calendar, invoice) {
  const buckets = new Map();
  for (const t of invoice) {
    if (!buckets.has(t.key)) buckets.set(t.key, []);
    buckets.get(t.key).push(t);
  }
  const matched = [];
  const calOnly = [];
  for (const c of calendar) {
    const b = buckets.get(c.key);
    if (b && b.length) {
      matched.push([c, b.shift()]);
    } else {
      calOnly.push(c);
    }
  }
  const invOnly = [];
  for (const list of buckets.values()) invOnly.push(...list);
  return { matched, calOnly, invOnly };
}

function buildReport(calName, invName, invoiceCount, matchedCount, invOnly) {
  const lines = [
    "INVOICE vs CALENDAR (did you book everything on the invoice?)",
    "=".repeat(72),
    `Calendar file: ${calName}`,
    `Invoice file:  ${invName}`,
    "",
    "SUMMARY",
    "-".repeat(72),
    `  Invoice trips found in file: ${invoiceCount}`,
    `  Also found in calendar export: ${matchedCount}`,
    `  NOT found in calendar export:  ${invOnly.length}`,
  ];
  if (!invOnly.length) {
    lines.push("", "  All invoice trips have a matching calendar booking (date + time + driver).");
  }
  lines.push("", "Match rule: same calendar date, same time, same driver (name normalised).", "");
  if (invOnly.length) {
    lines.push(
      "INVOICE TRIPS NOT IN YOUR CALENDAR EXPORT (book these or query the operator)",
      "-".repeat(72)
    );
    for (const t of invOnly) {
      lines.push(`  ${t.ymd} ${t.hhmm}  ${t.driver}  |  ${t.detail}`);
    }
    lines.push("");
  }
  lines.push("END");
  return lines.join("\n");
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = () => reject(r.error);
    r.readAsText(file);
  });
}

export async function runCompare(calendarFile, invoiceFile) {
  const [calText, invText] = await Promise.all([
    readFileAsText(calendarFile),
    readFileAsText(invoiceFile),
  ]);
  const calTrips = parseCalendarText(calText);
  const invTrips = parseInvoiceText(invText);
  if (!invTrips.length) {
    throw new Error("No invoice trips found. Check the ABC invoice .txt format.");
  }
  if (!calTrips.length) {
    throw new Error("No calendar bookings found. Check the TaxiCalendar .txt export.");
  }
  const { matched, invOnly } = multisetMatch(calTrips, invTrips);
  const report = buildReport(
    calendarFile.name,
    invoiceFile.name,
    invTrips.length,
    matched.length,
    invOnly
  );
  return { report, invOnly, matched, invoiceCount: invTrips.length };
}
