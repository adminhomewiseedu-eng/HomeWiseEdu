export const BIBLE_PROGRAMME = 'bible_study';

export function isBibleUser(user) {
  return user?.programme === BIBLE_PROGRAMME;
}

export function dashboardFor(user) {
  if (!user) return '/login';
  if (user.role === 'admin') return '/admin';
  if (isBibleUser(user)) return user.role === 'student' ? '/bible-study/student' : '/bible-study/parent';
  return user.role === 'student' ? '/student' : '/parent';
}

export function mayOpenProgrammeRoute(user, routeProgramme) {
  if (!user || user.role === 'admin') return Boolean(user);
  return routeProgramme === BIBLE_PROGRAMME ? isBibleUser(user) : !isBibleUser(user);
}

export function bibleSubjectsOnly(items = []) {
  return items.filter((item) => {
    const slug = item.slug || item.subject_slug;
    const name = item.subject || item.title || item.name;
    return slug === 'understanding-the-word' || String(name || '').toLowerCase() === 'understanding the word';
  });
}
