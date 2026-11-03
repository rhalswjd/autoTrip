const entryKey = 'autotrip.home.entered';
let enteredInMemory = false;

/** Storage is optional: restricted browsers can still enter and use the planner. */
export function hasEnteredHome(): boolean {
  try { return enteredInMemory || sessionStorage.getItem(entryKey) === 'yes'; }
  catch (error) { console.warn('Home intro preference could not be read.', error); return enteredInMemory; }
}

export function rememberHomeEntry(): void {
  enteredInMemory = true;
  try { sessionStorage.setItem(entryKey, 'yes'); }
  catch (error) { console.warn('Home intro preference is available for this page only.', error); }
}
