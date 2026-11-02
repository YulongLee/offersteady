/** Read only the application archive; never import or execute its contents. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import * as asar from '@electron/asar';

const archive = process.argv[2];
assert.ok(archive, 'archive_required');
const files = {};
let packageJson;
for (const entry of asar.listPackage(archive)) {
  const name = entry.replaceAll('\\', '/').replace(/^\//, '');
  assert.ok(name && !name.startsWith('/') && !name.split('/').includes('..'), 'unsafe_asar_path');
  const info = asar.statFile(archive, name, false);
  assert.ok(!info.link, 'asar_link_rejected');
  if (info.files) continue;
  const bytes = asar.extractFile(archive, name);
  assert.ok(!Object.hasOwn(files, name), 'duplicate_asar_path');
  files[name] = createHash('sha256').update(bytes).digest('hex');
  if (name === 'package.json') packageJson = JSON.parse(bytes.toString('utf8'));
}
assert.ok(packageJson, 'app_package_missing');
console.log(JSON.stringify({ files, packageJson }));
