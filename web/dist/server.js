import express from 'express';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
const ROOT = path.resolve('c:/Users/BetoCW´s/Documents/Plane');
const DATA_DIR = path.join(ROOT, 'data');
const PUBLIC_DIR = path.join(ROOT, 'web', 'public');
const MAIN_FILE = path.join(DATA_DIR, 'main.json');
function ensureDir(dir) {
    if (!fs.existsSync(dir))
        fs.mkdirSync(dir, { recursive: true });
}
ensureDir(DATA_DIR);
app.use(express.static(PUBLIC_DIR));
app.get('/api/datasets', (req, res) => {
    ensureDir(DATA_DIR);
    const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
    const hasMain = fs.existsSync(MAIN_FILE);
    res.json({ files, main: hasMain ? 'main.json' : null });
});
app.post('/api/add', (req, res) => {
    const { values, session, text } = req.body;
    // Accept either structured numbers or raw text like "2.95x, 2.15x, ..."
    let vals = [];
    if (text && typeof text === 'string') {
        const tokens = text.split(/[\s,]+/).filter(Boolean);
        for (const t of tokens) {
            const norm = t.replace(/x$/i, '').trim();
            const v = parseFloat(norm);
            if (!isNaN(v))
                vals.push(v);
        }
    }
    else if (values && Array.isArray(values)) {
        vals = values.filter(v => typeof v === 'number');
    }
    else {
        return res.status(400).json({ error: 'Provide values[] or text' });
    }
    ensureDir(DATA_DIR);
    vals = vals.filter(v => v >= 1);
    const recs = vals.map(v => ({ session_id: session || 'web', multiplier: v }));
    // Write to a new auto-named file for audit
    const stamp = new Date();
    const name = `session_${stamp.getFullYear()}${String(stamp.getMonth() + 1).padStart(2, '0')}${String(stamp.getDate()).padStart(2, '0')}-${String(stamp.getHours()).padStart(2, '0')}${String(stamp.getMinutes()).padStart(2, '0')}${String(stamp.getSeconds()).padStart(2, '0')}.json`;
    const newFile = path.join(DATA_DIR, name);
    fs.writeFileSync(newFile, JSON.stringify(recs));
    // Merge into MAIN_FILE to maintain single consolidated dataset
    let main = [];
    if (fs.existsSync(MAIN_FILE)) {
        try {
            main = JSON.parse(fs.readFileSync(MAIN_FILE, 'utf-8'));
        }
        catch { }
    }
    main = Array.isArray(main) ? main.concat(recs) : recs;
    fs.writeFileSync(MAIN_FILE, JSON.stringify(main));
    res.json({ added: vals.length, file: path.basename(newFile), main: 'main.json' });
});
app.post('/api/merge', (req, res) => {
    const { inputs } = req.body;
    if (!inputs)
        return res.status(400).json({ error: 'inputs[] required' });
    ensureDir(DATA_DIR);
    const rows = [];
    for (const p of inputs) {
        const inPath = path.isAbsolute(p) ? p : path.join(DATA_DIR, p);
        if (!fs.existsSync(inPath))
            continue;
        if (inPath.toLowerCase().endsWith('.json')) {
            try {
                const arr = JSON.parse(fs.readFileSync(inPath, 'utf-8'));
                if (Array.isArray(arr)) {
                    for (const r of arr) {
                        const m = parseFloat(String(r.multiplier));
                        if (!isNaN(m) && m >= 1)
                            rows.push({ session_id: String(r.session_id || path.basename(inPath)), multiplier: m });
                    }
                }
            }
            catch { }
        }
    }
    // Merge into MAIN_FILE
    let main = [];
    if (fs.existsSync(MAIN_FILE)) {
        try {
            main = JSON.parse(fs.readFileSync(MAIN_FILE, 'utf-8'));
        }
        catch { }
    }
    main = Array.isArray(main) ? main.concat(rows) : rows;
    fs.writeFileSync(MAIN_FILE, JSON.stringify(main));
    res.json({ merged: rows.length, main: 'main.json' });
});
const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
app.listen(PORT, () => {
    console.log(`Web UI running on http://localhost:${PORT}`);
});
// --- Añadir crash manual y resumen ---
function readMainValues() {
    try {
        const txt = fs.readFileSync(MAIN_FILE, 'utf-8');
        const arr = JSON.parse(txt);
        if (Array.isArray(arr))
            return arr.map((r) => Number(r.multiplier)).filter((v) => !isNaN(v) && v >= 1);
    }
    catch { }
    return [];
}
function writeAppendCrash(value, sessionId = 'real') {
    ensureDir(DATA_DIR);
    let mainArr = [];
    if (fs.existsSync(MAIN_FILE)) {
        try {
            const txt = fs.readFileSync(MAIN_FILE, 'utf-8');
            mainArr = JSON.parse(txt);
        }
        catch { }
    }
    if (!Array.isArray(mainArr))
        mainArr = [];
    mainArr.push({ session_id: sessionId, multiplier: value });
    fs.writeFileSync(MAIN_FILE, JSON.stringify(mainArr));
}
app.post('/api/add-crash', (req, res) => {
    const { value } = req.body;
    let v = 0;
    if (typeof value === 'string')
        v = parseFloat(value.replace(/x$/i, '').trim());
    else if (typeof value === 'number')
        v = value;
    if (!v || Number.isNaN(v) || v < 1)
        return res.status(400).json({ error: 'Valor inválido, debe ser >= 1' });
    try {
        writeAppendCrash(Number(v.toFixed(2)));
    }
    catch { }
    res.json({ added: 1, main: 'main.json' });
});
app.get('/api/summary', (req, res) => {
    const sample = readMainValues();
    const n = sample.length;
    const mean = n ? sample.reduce((a, b) => a + b, 0) / n : 0;
    let median = 0;
    if (n) {
        const s = [...sample].sort((a, b) => a - b);
        median = n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
    }
    const thresholds = [1.5, 2, 3, 5, 10];
    const pge = {};
    for (const t of thresholds) {
        const c = sample.filter(v => v >= t).length;
        pge[t.toFixed(2)] = n ? Number((c / n).toFixed(6)) : 0;
    }
    res.json({ n, mean: Number(mean.toFixed(6)), median: Number(median.toFixed(6)), pge });
});
// --- Simulación espejo: SSE que sube hasta crash R tomado del dataset ---
app.get('/api/sim-stream', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();
    const id = String(req.query.id || 'sim');
    const step = Number(req.query.step || 0.01);
    const period = Number(req.query.period || 100);
    function sampleCrash() {
        const sample = readMainValues();
        if (sample.length === 0) {
            const xm = 1.0;
            const alpha = 2.0; // Pareto fallback
            const u = Math.random();
            return xm * Math.pow(1 - u, -1 / alpha);
        }
        const idx = Math.floor(Math.random() * sample.length);
        return Math.max(1, Number(sample[idx].toFixed(2)));
    }
    let R = sampleCrash();
    let x = 1.0;
    const interval = setInterval(() => {
        x = Number((x + step).toFixed(2));
        if (x >= R) {
            res.write(`data: ${JSON.stringify({ type: 'crash', id, R })}\n\n`);
            try {
                writeAppendCrash(R, id);
            }
            catch { }
            R = sampleCrash();
            x = 1.0;
        }
        else {
            res.write(`data: ${JSON.stringify({ type: 'tick', id, x, R })}\n\n`);
        }
    }, period);
    req.on('close', () => clearInterval(interval));
});
// --- Real-time SSE: progressive thresholds and survival ---
app.get('/api/stream', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();
    // Load main.json and compute empirical survival on demand
    function loadValues() {
        try {
            const txt = fs.readFileSync(MAIN_FILE, 'utf-8');
            const arr = JSON.parse(txt);
            if (Array.isArray(arr))
                return arr.map((r) => Number(r.multiplier)).filter((v) => !isNaN(v) && v >= 1);
        }
        catch { }
        return [];
    }
    function survivalAt(x, sample) {
        const n = sample.length;
        if (n === 0)
            return 0;
        let c = 0;
        for (const v of sample)
            if (v >= x)
                c++;
        return c / n;
    }
    let x = 1.0;
    const step = 0.01;
    const interval = setInterval(() => {
        const sample = loadValues();
        const S = survivalAt(x, sample);
        const payload = { x: Number(x.toFixed(2)), S: Number(S.toFixed(6)), n: sample.length };
        res.write(`data: ${JSON.stringify(payload)}\n\n`);
        x += step;
        if (x > 1000)
            x = 1.0; // wrap defensively
    }, 200);
    req.on('close', () => {
        clearInterval(interval);
    });
});
// Provably Fair real-time stream: progressive rise until crash R per seeds
app.get('/api/pf-stream', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();
    const server = String(req.query.server || '');
    const client = String(req.query.client || '');
    let nonce = Number(req.query.nonce || 0);
    const edge = Number(req.query.edge || 0.99);
    const step = Number(req.query.step || 0.01);
    const period = Number(req.query.period || 100);
    if (!server || !client || Number.isNaN(nonce)) {
        res.write(`data: ${JSON.stringify({ error: 'server, client, nonce required' })}\n\n`);
    }
    function hmacHex(serverSeed, clientSeed, n) {
        const h = crypto.createHmac('sha256', Buffer.from(serverSeed, 'utf-8'))
            .update(Buffer.from(`${clientSeed}${n}`, 'utf-8'))
            .digest('hex');
        return h;
    }
    function toUniform(hex) {
        const head = hex.slice(0, 13);
        const num = parseInt(head, 16);
        const denom = Math.pow(16, head.length);
        return num / denom;
    }
    function crashR(serverSeed, clientSeed, n, houseEdge) {
        const u = toUniform(hmacHex(serverSeed, clientSeed, n));
        const x = Math.max(Math.min(u, 1 - 1e-12), 1e-12);
        return Math.max(1.0, houseEdge / (1 - x));
    }
    let R = crashR(server, client, nonce, edge);
    let x = 1.0;
    const interval = setInterval(() => {
        x = Number((x + step).toFixed(2));
        if (x >= R) {
            const crashVal = Number(R.toFixed(2));
            res.write(`data: ${JSON.stringify({ type: 'crash', R: crashVal, nonce })}\n\n`);
            // Persist crash as a new datum in main.json
            try {
                ensureDir(DATA_DIR);
                let mainArr = [];
                if (fs.existsSync(MAIN_FILE)) {
                    try {
                        const txt = fs.readFileSync(MAIN_FILE, 'utf-8');
                        mainArr = JSON.parse(txt);
                    }
                    catch { }
                }
                if (!Array.isArray(mainArr))
                    mainArr = [];
                mainArr.push({ session_id: 'pf', multiplier: crashVal });
                fs.writeFileSync(MAIN_FILE, JSON.stringify(mainArr));
            }
            catch { }
            // next round
            nonce += 1;
            R = crashR(server, client, nonce, edge);
            x = 1.0;
        }
        else {
            res.write(`data: ${JSON.stringify({ type: 'tick', x, R: Number(R.toFixed(2)), nonce })}\n\n`);
        }
    }, period);
    req.on('close', () => clearInterval(interval));
});
