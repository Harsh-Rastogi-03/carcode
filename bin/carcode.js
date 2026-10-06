#!/usr/bin/env node
// carcode launcher for npm: `npx carcode-cli` installs carcode, `npx carcode-cli <command>` runs it.
//
// carcode itself is a small Python server plus a bash CLI. The background services
// need a folder that doesn't move, so this launcher keeps a copy in ~/.carcode
// (override with CARCODE_HOME) and refreshes it when the package version changes.
// Your settings (.env), token and logs (data/) and private context are never touched.

"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const PKG_DIR = path.resolve(__dirname, "..");
const VERSION = require(path.join(PKG_DIR, "package.json")).version;
const HOME = process.env.CARCODE_HOME || path.join(os.homedir(), ".carcode");

// Files the app needs at runtime. Everything else in HOME belongs to the user.
const APP_FILES = [
  "carcode", "install.sh", "run_server.sh", "run_tunnel.sh",
  "server.py", "talk.py", "make_shortcut.py", "ui.html",
  "prompts/assistant.md", ".env.example", "pyproject.toml", "uv.lock",
  "AGENTS.md", "LICENSE", "README.md",
];
const EXECUTABLES = new Set(["carcode", "install.sh", "run_server.sh", "run_tunnel.sh"]);

function fail(message) {
  process.stderr.write(`\x1b[31m${message}\x1b[0m\n`);
  process.exit(1);
}

function installedVersion() {
  try {
    return fs.readFileSync(path.join(HOME, ".version"), "utf8").trim();
  } catch {
    return null;
  }
}

/** Copy this package's app files into HOME. Returns true if anything changed. */
function sync() {
  if (installedVersion() === VERSION && fs.existsSync(path.join(HOME, "carcode"))) return false;
  for (const file of APP_FILES) {
    const from = path.join(PKG_DIR, file);
    if (!fs.existsSync(from)) continue;
    const to = path.join(HOME, file);
    fs.mkdirSync(path.dirname(to), { recursive: true });
    fs.copyFileSync(from, to);
    if (EXECUTABLES.has(file)) fs.chmodSync(to, 0o755);
  }
  fs.writeFileSync(path.join(HOME, ".version"), `${VERSION}\n`);
  return true;
}

function run(file, args, extraEnv = {}) {
  const result = spawnSync("bash", [path.join(HOME, file), ...args], {
    cwd: HOME,
    stdio: "inherit",
    env: { ...process.env, CARCODE_CMD: "npx carcode-cli", ...extraEnv },
  });
  if (result.error) fail(result.error.message);
  return result.status ?? 1;
}

function main() {
  if (process.platform !== "darwin") {
    fail("carcode needs a Mac: the Siri Shortcut is signed there and the services run with launchd.");
  }
  const args = process.argv.slice(2);
  const first = args[0];
  const previous = installedVersion();
  const changed = sync();

  // `npx carcode-cli` or `npx carcode-cli --yes --workdir ~/code`: run the guided installer.
  if (!first || first === "init" || first.startsWith("-")) {
    const installerArgs = first === "init" ? args.slice(1) : args;
    process.exit(run("install.sh", ["--source", HOME, ...installerArgs]));
  }

  if (first === "update") {
    if (changed && previous) console.log(`Updated carcode ${previous} → ${VERSION}.`);
    else console.log(`carcode ${VERSION} is current. For the newest release run: npx carcode-cli@latest update`);
    process.exit(run("carcode", ["restart-if-installed"]));
  }

  if (first === "where") {
    console.log(HOME);
    process.exit(0);
  }

  process.exit(run("carcode", args));
}

main();
