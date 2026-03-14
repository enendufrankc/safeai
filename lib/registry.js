'use strict';

const fs = require('node:fs');
const path = require('node:path');
const https = require('node:https');

const BUNDLED_REGISTRY = path.join(__dirname, '..', 'skills-registry.json');
const REMOTE_REGISTRY_URL = 'https://raw.githubusercontent.com/enendufrankc/safeai/main/skills-registry.json';

/**
 * Load the skills registry. Tries remote first, falls back to bundled.
 */
async function loadRegistry(opts = {}) {
  if (opts.offline) {
    return readBundled();
  }
  try {
    const remote = await fetchRemote(REMOTE_REGISTRY_URL, 3000);
    return JSON.parse(remote);
  } catch {
    return readBundled();
  }
}

function readBundled() {
  return JSON.parse(fs.readFileSync(BUNDLED_REGISTRY, 'utf8'));
}

function fetchRemote(url, timeoutMs) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { timeout: timeoutMs }, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        return;
      }
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks).toString()));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

/**
 * Find a skill entry by name in the registry.
 */
async function findSkill(name, opts = {}) {
  const registry = await loadRegistry(opts);
  return registry.skills.find((s) => s.name === name) || null;
}

/**
 * Search skills by query string (matches name, description, tags).
 */
async function searchSkills(query, opts = {}) {
  const registry = await loadRegistry(opts);
  if (!query) return registry.skills;
  const q = query.toLowerCase();
  return registry.skills.filter((s) =>
    s.name.includes(q) ||
    s.description.toLowerCase().includes(q) ||
    (s.tags || []).some((t) => t.includes(q)) ||
    (s.category || '').includes(q)
  );
}

module.exports = { loadRegistry, findSkill, searchSkills };
