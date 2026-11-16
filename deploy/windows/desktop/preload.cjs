// Seed this desktop profile once; preserve later language choices across upgrades.
if (window.location.protocol === 'http:' && window.location.hostname === '127.0.0.1') {
  if (!localStorage.getItem('arcreel_desktop_locale_initialized')) {
    localStorage.setItem('i18nextLng', 'zh');
    localStorage.setItem('arcreel_desktop_locale_initialized', '1');
  }
}
