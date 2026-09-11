export function preserveRealtimeTrace(path, currentSearch = '') {
  const active = new URLSearchParams(currentSearch).get('realtimeTrace') === '1';
  if (!active) return path;

  const [pathname, query = ''] = String(path).split('?');
  const params = new URLSearchParams(query);
  params.set('realtimeTrace', '1');
  return `${pathname}?${params.toString()}`;
}
