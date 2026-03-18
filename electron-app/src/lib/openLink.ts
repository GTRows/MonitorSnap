export function openLink(url: string): void {
  if (window.api?.openExternal) {
    window.api.openExternal(url);
  } else {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}
