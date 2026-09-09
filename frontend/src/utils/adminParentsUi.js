export const parentPageCount = (total, pageSize) => Math.max(1, Math.ceil(Number(total || 0) / Number(pageSize || 1)));

export const emptyParentsMessage = (search) => search?.trim()
  ? 'Search returned no results.'
  : 'No parents found.';

export const nextParentStatus = (status) => status === 'active' ? 'suspended' : 'active';

export const parentStatusAction = (status) => status === 'active' ? 'Suspend' : 'Reactivate';
