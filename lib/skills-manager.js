'use strict';

const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const https = require('node:https');
const http = require('node:http');
const { execSync } = require('node:child_process');

const { findSkill, searchSkills, loadRegistry } = require('./registry.js');

const LOCK_FILE = '.safeai/skills.json';
const SKILLS_DIR = '.safeai/skills';

// Where skill file types are installed (relative to project root)
const DEST_MAP = {
  'plugins':   'plugins',
  'policies':  'policies',
  'contracts': 'contracts',
  'schemas':   'schemas',
  'agents':    'agents',
  'skill':     null,  // handled specially → .safeai/skills/<name>/
};

class SkillsManager {
  constructor(projectRoot) {
    this.root = projectRoot;
    this.lockPath = path.join(projectRoot, LOCK_FILE);
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  async add(nameOrSource, flags = []) {
    const { name, source } = await this._resolveSource(nameOrSource);
    const lock = this._readLock();

    if (lock.installed[name] && !flags.includes('--force')) {
      const current = lock.installed[name].version;
      console.log(`  [i] ${name}@${current} is already installed. Use --force to reinstall.`);
      return;
    }

    console.log(`\n  Installing skill: ${name} (${source})\n`);

    const tmpDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'safeai-skill-'));
    try {
      const skillDir = await this._download(source, tmpDir, name);
      const manifest = this._readManifest(skillDir);
      const installedFiles = await this._installFiles(skillDir, manifest, name);

      lock.installed[name] = {
        version: manifest.version || 'unknown',
        source,
        installed_at: new Date().toISOString(),
        files: installedFiles,
      };
      this._writeLock(lock);

      console.log(`\n  ✓ Installed: ${name}@${manifest.version || 'unknown'}`);
      if (manifest.description) console.log(`    ${manifest.description}`);
      if (installedFiles.length) {
        console.log(`\n  Files installed:`);
        installedFiles.forEach((f) => console.log(`    · ${f}`));
      }
      if (manifest.postInstall) {
        console.log(`\n  Post-install note:\n    ${manifest.postInstall}`);
      }
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  }

  async remove(name) {
    const lock = this._readLock();
    const entry = lock.installed[name];
    if (!entry) {
      console.log(`  [i] Skill '${name}' is not installed.`);
      return;
    }

    const removed = [];
    for (const rel of entry.files || []) {
      const abs = path.join(this.root, rel);
      if (fs.existsSync(abs)) {
        fs.rmSync(abs, { recursive: true, force: true });
        removed.push(rel);
      }
    }

    // Remove skill dir if empty
    const skillDir = path.join(this.root, SKILLS_DIR, name);
    if (fs.existsSync(skillDir)) {
      fs.rmSync(skillDir, { recursive: true, force: true });
    }

    delete lock.installed[name];
    this._writeLock(lock);

    console.log(`\n  ✓ Removed: ${name}`);
    removed.forEach((f) => console.log(`    · ${f}`));
  }

  async list() {
    const lock = this._readLock();
    const entries = Object.entries(lock.installed);

    if (entries.length === 0) {
      console.log('\n  No skills installed yet.\n  Run: npx safeai-sdk skills search\n');
      return;
    }

    console.log(`\n  Installed skills (${entries.length}):\n`);
    for (const [name, info] of entries) {
      console.log(`  · ${name}@${info.version}  [${info.source}]`);
      console.log(`    Installed: ${info.installed_at}`);
      console.log(`    Files: ${(info.files || []).length}`);
    }
    console.log('');
  }

  async search(query) {
    const results = await searchSkills(query);

    if (results.length === 0) {
      console.log(`\n  No skills found${query ? ` for "${query}"` : ''}.\n`);
      return;
    }

    const lock = this._readLock();
    const label = query ? `Skills matching "${query}"` : 'Available skills';
    console.log(`\n  ${label} (${results.length}):\n`);

    for (const s of results) {
      const installed = lock.installed[s.name] ? ` [installed ${lock.installed[s.name].version}]` : '';
      console.log(`  · ${s.name}@${s.version}${installed}`);
      console.log(`    ${s.description}`);
      console.log(`    Category: ${s.category}  Tags: ${(s.tags || []).join(', ')}`);
      console.log(`    Install:  npx safeai-sdk add ${s.name}\n`);
    }
  }

  // -------------------------------------------------------------------------
  // Source resolution
  // -------------------------------------------------------------------------

  async _resolveSource(input) {
    // Local path
    if (input.startsWith('./') || input.startsWith('/') || input.startsWith('../')) {
      const abs = path.resolve(this.root, input);
      const manifest = this._readManifest(abs);
      return { name: manifest.name, source: `local:${abs}` };
    }

    // npm: prefix
    if (input.startsWith('npm:')) {
      const pkg = input.slice(4);
      return { name: pkg.replace(/^safeai-skill-/, ''), source: input };
    }

    // github: prefix
    if (input.startsWith('github:')) {
      const parts = input.slice(7).split('/');
      const name = parts[parts.length - 1].replace(/^safeai-skill-/, '');
      return { name, source: input };
    }

    // Registry lookup
    const entry = await findSkill(input, { offline: false });
    if (entry) {
      return { name: entry.name, source: entry.source };
    }

    // Fall back to treating as npm package name
    return { name: input.replace(/^safeai-skill-/, ''), source: `npm:safeai-skill-${input}` };
  }

  // -------------------------------------------------------------------------
  // Download
  // -------------------------------------------------------------------------

  async _download(source, tmpDir, name) {
    if (source.startsWith('local:')) {
      return source.slice(6);
    }

    if (source.startsWith('npm:')) {
      return this._downloadNpm(source.slice(4), tmpDir);
    }

    if (source.startsWith('github:')) {
      return this._downloadGitHub(source.slice(7), tmpDir, name);
    }

    throw new Error(`Unknown source format: ${source}`);
  }

  _downloadNpm(pkg, tmpDir) {
    console.log(`  Downloading from npm: ${pkg}`);
    try {
      execSync(`npm pack ${pkg} --pack-destination "${tmpDir}" --quiet`, {
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (e) {
      throw new Error(`npm pack failed for '${pkg}': ${e.message}`);
    }

    const tarballs = fs.readdirSync(tmpDir).filter((f) => f.endsWith('.tgz'));
    if (!tarballs.length) throw new Error(`npm pack produced no tarball for ${pkg}`);

    const tarball = path.join(tmpDir, tarballs[0]);
    const extractDir = path.join(tmpDir, 'extracted');
    fs.mkdirSync(extractDir);
    execSync(`tar xzf "${tarball}" -C "${extractDir}"`, { stdio: 'inherit' });

    // npm packs into a 'package/' subdirectory
    const packageDir = path.join(extractDir, 'package');
    return fs.existsSync(packageDir) ? packageDir : extractDir;
  }

  async _downloadGitHub(spec, tmpDir, name) {
    // spec: user/repo  or  user/repo/subpath  or  user/repo@ref
    const [repoSpec, subpath] = spec.includes('/') && spec.split('/').length > 2
      ? [spec.split('/').slice(0, 2).join('/'), spec.split('/').slice(2).join('/')]
      : [spec, null];

    const [repoAndRef, ref = 'main'] = repoSpec.split('@');
    const [user, repo] = repoAndRef.split('/');
    const zipUrl = `https://github.com/${user}/${repo}/archive/refs/heads/${ref}.zip`;

    console.log(`  Downloading from GitHub: ${user}/${repo}@${ref}`);

    const zipPath = path.join(tmpDir, 'skill.zip');
    await this._downloadFile(zipUrl, zipPath);

    const extractDir = path.join(tmpDir, 'extracted');
    fs.mkdirSync(extractDir);
    execSync(`unzip -q "${zipPath}" -d "${extractDir}"`);

    // GitHub zip has a root folder like repo-ref/
    const rootFolders = fs.readdirSync(extractDir);
    let skillDir = path.join(extractDir, rootFolders[0]);

    if (subpath) {
      skillDir = path.join(skillDir, subpath);
    }

    return skillDir;
  }

  _downloadFile(url, dest) {
    return new Promise((resolve, reject) => {
      const client = url.startsWith('https') ? https : http;
      const file = fs.createWriteStream(dest);

      function request(requestUrl) {
        client.get(requestUrl, (res) => {
          if (res.statusCode === 301 || res.statusCode === 302) {
            file.close();
            request(res.headers.location);
            return;
          }
          if (res.statusCode !== 200) {
            reject(new Error(`HTTP ${res.statusCode} for ${requestUrl}`));
            return;
          }
          res.pipe(file);
          file.on('finish', () => file.close(resolve));
        }).on('error', reject);
      }

      request(url);
    });
  }

  // -------------------------------------------------------------------------
  // Manifest
  // -------------------------------------------------------------------------

  _readManifest(skillDir) {
    const manifestPath = path.join(skillDir, 'safeai-skill.json');
    if (!fs.existsSync(manifestPath)) {
      // Try to infer from package.json or SKILL.md
      const pkgPath = path.join(skillDir, 'package.json');
      if (fs.existsSync(pkgPath)) {
        const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
        return { name: pkg.name, version: pkg.version, description: pkg.description };
      }
      // Minimal manifest — will still install by directory structure
      return { name: path.basename(skillDir), version: 'unknown' };
    }
    return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  }

  // -------------------------------------------------------------------------
  // File installation
  // -------------------------------------------------------------------------

  async _installFiles(skillDir, manifest, name) {
    const installed = [];

    for (const entry of fs.readdirSync(skillDir)) {
      const srcPath = path.join(skillDir, entry);
      const stat = fs.statSync(srcPath);

      if (stat.isDirectory()) {
        if (entry === 'skill') {
          // Agent skill directory → .safeai/skills/<name>/
          const dest = path.join(this.root, SKILLS_DIR, name);
          this._ensureDir(dest);
          this._copyDir(srcPath, dest);
          installed.push(`${SKILLS_DIR}/${name}`);
        } else if (DEST_MAP[entry] !== undefined) {
          // Known directory → copy each file into project's matching dir
          const destDir = path.join(this.root, DEST_MAP[entry]);
          this._ensureDir(destDir);
          for (const file of this._listFiles(srcPath)) {
            const rel = path.relative(srcPath, file);
            const dest = path.join(destDir, rel);
            this._ensureDir(path.dirname(dest));
            fs.copyFileSync(file, dest);
            installed.push(path.join(DEST_MAP[entry], rel));
          }
        }
      } else if (entry === 'plugin.py') {
        // Top-level plugin.py → plugins/<name>.py
        this._ensureDir(path.join(this.root, 'plugins'));
        const dest = path.join(this.root, 'plugins', `${name}.py`);
        fs.copyFileSync(srcPath, dest);
        installed.push(`plugins/${name}.py`);
      }
    }

    return installed;
  }

  // -------------------------------------------------------------------------
  // Lock file
  // -------------------------------------------------------------------------

  _readLock() {
    if (!fs.existsSync(this.lockPath)) {
      return { version: '1', installed: {} };
    }
    try {
      return JSON.parse(fs.readFileSync(this.lockPath, 'utf8'));
    } catch {
      return { version: '1', installed: {} };
    }
  }

  _writeLock(lock) {
    this._ensureDir(path.dirname(this.lockPath));
    fs.writeFileSync(this.lockPath, JSON.stringify(lock, null, 2));
  }

  // -------------------------------------------------------------------------
  // Utils
  // -------------------------------------------------------------------------

  _ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  }

  _copyDir(src, dest) {
    this._ensureDir(dest);
    for (const entry of fs.readdirSync(src)) {
      const srcPath = path.join(src, entry);
      const destPath = path.join(dest, entry);
      if (fs.statSync(srcPath).isDirectory()) {
        this._copyDir(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }

  _listFiles(dir) {
    const files = [];
    for (const entry of fs.readdirSync(dir)) {
      const full = path.join(dir, entry);
      if (fs.statSync(full).isDirectory()) {
        files.push(...this._listFiles(full));
      } else {
        files.push(full);
      }
    }
    return files;
  }
}

module.exports = { SkillsManager };
