const path = require('node:path');
const fs = require('node:fs');
const { MSICreator } = require('electron-wix-msi');

const projectRoot = path.resolve(__dirname, '..');
const releaseDir = path.join(projectRoot, 'release');
const appDirectory = path.join(releaseDir, 'win-unpacked');

const pkg = JSON.parse(fs.readFileSync(path.join(projectRoot, 'package.json'), 'utf8'));

async function main() {
  if (!fs.existsSync(appDirectory)) {
    throw new Error(`Expected ${appDirectory} to exist. Run electron-builder first.`);
  }

  const msiCreator = new MSICreator({
    appDirectory,
    outputDirectory: releaseDir,
    exe: 'MonitorSnap',
    name: 'MonitorSnap',
    manufacturer: 'GTRows',
    version: pkg.version,
    description: pkg.description,
    shortcutName: 'MonitorSnap',
    shortcutFolderName: 'MonitorSnap',
    appIconPath: path.join(projectRoot, 'public', 'icon.ico'),
    ui: {
      chooseDirectory: true,
    },
  });

  await msiCreator.create();
  const { supportBinaries } = await msiCreator.compile();

  const srcMsi = path.join(releaseDir, 'MonitorSnap.msi');
  const dstMsi = path.join(releaseDir, `MonitorSnap-${pkg.version}.msi`);
  if (fs.existsSync(srcMsi)) {
    fs.renameSync(srcMsi, dstMsi);
    console.log(`MSI: ${dstMsi}`);
  } else {
    console.error(`MSICreator finished but ${srcMsi} was not produced.`);
    console.error('Files in release dir:');
    for (const f of fs.readdirSync(releaseDir)) console.error(`  ${f}`);
    process.exit(1);
  }

  if (supportBinaries && supportBinaries.length) {
    console.log(`Support binaries: ${supportBinaries.join(', ')}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
