// Upload a local image/audio/video to ListenHub storage; prints {"fileUrl": "..."}.
// Usage: node lh_upload.mjs <file>
// Reuses the ListenHub CLI's own SDK and saved API key (never prints the key).
// Honors LISTENHUB_OPENAPI_URL and the domain pinned with `listenhub config` (e.g. users in mainland China).
import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

try {
  const file = process.argv[2];
  if (!file || !fs.existsSync(file)) throw new Error("File not found: " + file);
  const root = execSync("npm root -g").toString().trim();
  const sdkDir = path.join(root, "@marswave", "listenhub-cli", "node_modules", "@marswave", "listenhub-sdk");
  if (!fs.existsSync(sdkDir)) throw new Error("ListenHub CLI not found. Run: npm install -g @marswave/listenhub-cli@latest");
  const pkg = JSON.parse(fs.readFileSync(path.join(sdkDir, "package.json"), "utf8"));
  const entry = typeof pkg.exports === "string" ? pkg.exports : (pkg.module ?? "dist/index.mjs");
  const { OpenAPIClient, DOMAIN_BASE_URLS } = await import(pathToFileURL(path.join(sdkDir, entry)).href);

  const cfgDir = path.join(process.env.XDG_CONFIG_HOME ?? path.join(os.homedir(), ".config"), "listenhub");
  const readJson = (p) => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return {}; } };

  let apiKey = process.env.LISTENHUB_API_KEY || readJson(path.join(cfgDir, "openapi.json")).apiKey;
  if (!apiKey) throw new Error("No API key. Run: listenhub openapi config set-key");

  let baseURL = process.env.LISTENHUB_OPENAPI_URL;
  const domain = readJson(path.join(cfgDir, "config.json")).domain;
  if (!baseURL && domain && domain !== "auto" && DOMAIN_BASE_URLS?.[domain]?.openapi) {
    baseURL = DOMAIN_BASE_URLS[domain].openapi;
  }

  const types = { ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac",
    ".mp4": "video/mp4", ".mov": "video/quicktime" };
  const contentType = types[path.extname(file).toLowerCase()];
  if (!contentType) throw new Error("Unsupported file type: " + path.extname(file));
  const limit = contentType.startsWith("image/") ? 10 : contentType.startsWith("audio/") ? 20 : 50;
  const size = fs.statSync(file).size;
  if (size > limit * 1024 * 1024) throw new Error(`File too large: ${(size / 1048576).toFixed(1)} MB (max ${limit} MB)`);

  const category = contentType.startsWith("image/") ? "banana" : "episode";
  const client = new OpenAPIClient(baseURL ? { apiKey, baseURL } : { apiKey });
  const { presignedUrl, fileUrl } = await client.createFileUpload({ fileKey: path.basename(file), contentType, category });
  const buf = fs.readFileSync(file);
  const res = await fetch(presignedUrl, { method: "PUT", body: buf,
    headers: { "Content-Type": contentType, "Content-Length": String(buf.length) } });
  if (!res.ok) throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  console.log(JSON.stringify({ fileUrl }));
} catch (e) {
  console.error("UPLOAD_ERROR: " + (e?.message ?? e));
  process.exit(1);
}
