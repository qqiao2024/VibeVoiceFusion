#!/usr/bin/env node
/**
 * Generate version string from git describe
 * Format: {tag}-g{commit_id} (e.g., v2.0.0-1-gc834ed1)
 *
 * This script creates a .env.local file with NEXT_PUBLIC_APP_VERSION
 * Run before `npm run dev` or `npm run build`
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function getGitVersion() {
  try {
    // git describe --tags --always provides format like:
    // - "v2.0.0" (if on exact tag)
    // - "v2.0.0-1-gc834ed1" (if 1 commit after tag)
    // - "c834ed1" (if no tags exist, just the short commit)
    const version = execSync('git describe --tags --always', {
      encoding: 'utf-8',
      cwd: path.resolve(__dirname, '../..'), // Go to project root
    }).trim();

    return version;
  } catch (error) {
    console.warn('Warning: Could not get git version, using fallback');
    console.warn(error.message);
    return 'unknown';
  }
}

function main() {
  const version = getGitVersion();
  const envPath = path.resolve(__dirname, '../.env.local');

  // Read existing .env.local if it exists
  let existingContent = '';
  try {
    existingContent = fs.readFileSync(envPath, 'utf-8');
  } catch (e) {
    // File doesn't exist, that's fine
  }

  // Parse existing env vars
  const envVars = {};
  existingContent.split('\n').forEach(line => {
    const match = line.match(/^([^=]+)=(.*)$/);
    if (match && match[1] !== 'NEXT_PUBLIC_APP_VERSION') {
      envVars[match[1]] = match[2];
    }
  });

  // Add/update version
  envVars['NEXT_PUBLIC_APP_VERSION'] = version;

  // Write back
  const newContent = Object.entries(envVars)
    .map(([key, value]) => `${key}=${value}`)
    .join('\n') + '\n';

  fs.writeFileSync(envPath, newContent);

  console.log(`Version: ${version}`);
}

main();
