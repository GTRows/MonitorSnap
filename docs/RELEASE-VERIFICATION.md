# Release verification

## v2.6.2 — checked 2026-11-04

The four packages were downloaded from the [v2.6.2 GitHub release](https://github.com/GTRows/MonitorSnap/releases/tag/v2.6.2).
Each locally calculated SHA-256 matched the corresponding asset's `digest` in the GitHub Releases API.

| Package | SHA-256 |
| --- | --- |
| `MonitorSnap-Setup-2.6.2.exe` | `c0b914e05988496baebc0e3872647a0ba8a94069ce2ef92344de5a494ae16522` |
| `MonitorSnap-2.6.2.msi` | `7dc59786f746cb07cdaded37698fa0dcd698e08826ce211cf5d2ac2e7aaaa37b` |
| `MonitorSnap-Portable-2.6.2.exe` | `e94204a229d9229db4f96fc2d03e788c6a0fbe51a060caacbfae057e7772287b` |
| `MonitorSnap-2.6.2-win.zip` | `97314a7915b7b8b4c3d45653ca52d5bff4b04c21ccebe0d89362c190b68758ef` |

### Package review status

Last checked: 2026-11-04. Each package is tracked separately; a result for one package does not approve the others.

| Package | Local Defender scan | Microsoft review | VirusTotal |
| --- | --- | --- | --- |
| Installer EXE | No threats found | Submitted; analyst decision pending | Upload blocked by reCAPTCHA connection error; no report |
| MSI | No threats found | Submitted; analyst decision pending | Upload blocked by reCAPTCHA connection error; no report |
| Portable EXE | No threats found | Submitted; analyst decision pending | Upload blocked by reCAPTCHA connection error; no report |
| ZIP, including extracted contents for the local scan | No threats found | Prepared; human verification not yet completed | Upload blocked by reCAPTCHA connection error; no report |

All four local scans used the engine and definitions listed below. None of these packages currently has a Microsoft analyst approval or a completed VirusTotal report in this record.

### Local antivirus scan

Microsoft Defender Antivirus scanned the four downloaded packages and the extracted ZIP contents on 2026-11-04.
`MpCmdRun.exe -Scan -ScanType 3 -File <download-directory> -DisableRemediation` returned exit code `0` and reported **found no threats**.

- Product version: `4.18.26100.4`
- Engine version: `1.1.26100.4`
- Security intelligence version: `1.463.119.0`

This is a dated local scan with one antivirus engine. It is not a Microsoft analyst approval, a VirusTotal report, or a guarantee about every antivirus product or future release.
The MSI and both EXE packages were also checked with `Get-AuthenticodeSignature`: all three returned `NotSigned`.

### SmartScreen and detection reports

[Microsoft documents](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) that SmartScreen checks download and signing-certificate reputation as well as known malicious files.
An unknown-publisher or low-reputation warning alone does not identify a particular malware detection. Code signing does not guarantee immediate SmartScreen reputation.

If a security product reports a named threat, preserve the file hash and detection details so the exact package can be investigated and, when appropriate, submitted to that vendor for review.
Microsoft provides an official [software developer submission portal](https://www.microsoft.com/en-us/wdsi/filesubmission).
The v2.6.2 MSI was submitted there on 2026-11-04 with the exact Edge "isn't commonly downloaded" warning and its SHA-256. The Installer EXE and Portable EXE were also received as separate review requests. The ZIP's current status is listed above. Analyst decisions are pending; no named malware detection has been reported for the additional packages.
This is a review request, not an approval or a guaranteed removal of the reputation warning. [Microsoft's developer guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) explains that consumer SmartScreen reputation builds over time and signing does not guarantee an immediate warning-free download.
No Microsoft analyst approval or completed code-signing application is claimed by this record.
