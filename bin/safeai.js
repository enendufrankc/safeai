#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 SafeAI Contributors
'use strict';

const path = require('node:path');
const { SkillsManager } = require('../lib/skills-manager.js');
const pkg = require('../package.json');

const HELP = `
safeai-sdk v${pkg.version}
SafeAI zero-trust security layer — skills installer

USAGE
  npx safeai-sdk <command> [args] [flags]

COMMANDS
  add <skill>             Install a skill into the current project
  install <skill>         Alias for add
  remove <skill>          Uninstall a skill from the current project
  skills list             List installed skills
  skills search [query]   Browse available skills from the registry
  --version               Print version

SKILL SOURCES
  <name>                  Install by name from the SafeAI skills registry
  npm:<package>           Install directly from npm
  github:<user>/<repo>    Install from a GitHub repository (default branch: main)
  github:<user>/<repo>@<ref>  Install from a specific branch or tag
  github:<user>/<repo>/<subpath>  Install a skill subdirectory from a GitHub repo
  ./path/to/skill         Install from a local directory

FLAGS
  --force                 Reinstall even if already installed
  --project-path <path>   Target project directory (default: cwd)

EXAMPLES
  npx safeai-sdk add langchain-adapter
  npx safeai-sdk add healthcare-policies
  npx safeai-sdk add github:enendufrankc/safeai-skills/safeai-deploy
  npx safeai-sdk add npm:safeai-skill-langchain
  npx safeai-sdk add ./my-custom-skill
  npx safeai-sdk remove langchain-adapter
  npx safeai-sdk skills list
  npx safeai-sdk skills search compliance

SKILL STRUCTURE
  A skill package should contain a safeai-skill.json manifest and any of:
    plugin.py / plugins/     → installed to <project>/plugins/
    policies/                → installed to <project>/policies/
    contracts/               → installed to <project>/contracts/
    schemas/                 → installed to <project>/schemas/
    agents/                  → installed to <project>/agents/
    skill/                   → installed to <project>/.safeai/skills/<name>/

  Installed skills are tracked in <project>/.safeai/skills.json
`;

async function main() {
  const rawArgs = process.argv.slice(2);

  if (rawArgs.length === 0 || rawArgs[0] === '--help' || rawArgs[0] === '-h') {
    console.log(HELP);
    return;
  }

  if (rawArgs[0] === '--version' || rawArgs[0] === '-v') {
    console.log(pkg.version);
    return;
  }

  // Parse --project-path flag
  let projectPath = process.cwd();
  const args = [];
  for (let i = 0; i < rawArgs.length; i++) {
    if (rawArgs[i] === '--project-path' && rawArgs[i + 1]) {
      projectPath = require('node:path').resolve(rawArgs[++i]);
    } else {
      args.push(rawArgs[i]);
    }
  }

  const command = args[0];
  const rest = args.slice(1);
  const flags = rest.filter((a) => a.startsWith('--'));
  const positional = rest.filter((a) => !a.startsWith('--'));

  const manager = new SkillsManager(projectPath);

  switch (command) {
    case 'add':
    case 'install': {
      if (!positional[0]) {
        console.error('  Error: skill name or source required.\n  Usage: safeai add <skill>');
        process.exit(1);
      }
      await manager.add(positional[0], flags);
      break;
    }

    case 'remove':
    case 'uninstall': {
      if (!positional[0]) {
        console.error('  Error: skill name required.\n  Usage: safeai remove <skill>');
        process.exit(1);
      }
      await manager.remove(positional[0]);
      break;
    }

    case 'skills': {
      const sub = positional[0];
      if (sub === 'list' || !sub) {
        await manager.list();
      } else if (sub === 'search') {
        await manager.search(positional[1]);
      } else {
        console.error(`  Unknown skills subcommand: ${sub}`);
        console.log('  Usage: safeai skills <list|search> [query]');
        process.exit(1);
      }
      break;
    }

    default: {
      console.error(`  Unknown command: ${command}\n`);
      console.log(HELP);
      process.exit(1);
    }
  }
}

main().catch((err) => {
  console.error(`\n  Error: ${err.message}`);
  if (process.env.SAFEAI_DEBUG) console.error(err.stack);
  process.exit(1);
});
