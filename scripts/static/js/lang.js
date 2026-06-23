/**
 * WIDDX Nexus — Localization / i18n Engine
 * Supports: English (LTR) and Arabic (RTL)
 *
 * Usage:
 *   Lang.t('key')           → translated string
 *   Lang.setLang('ar')      → switch to Arabic + RTL
 *   Lang.setLang('en')      → switch to English + LTR
 *   Lang.currentLang        → 'en' | 'ar'
 *   Lang.isRTL()            → true if Arabic
 */

const _translations = {
  en: {
    // Brand
    brand_name: 'WIDDX Nexus',
    brand_badge: 'v3',

    // Sidebar
    new_chat: 'New chat',
    nav_chat: 'Chat',
    nav_dashboard: 'Dashboard',
    nav_settings: 'Settings',
    nav_live: '● Live',

    // User
    user_name: 'WIDDX User',
    user_connected: 'Connected',

    // Chat Header
    header_switch_model: 'Switch Model',
    header_open_settings: 'Open Settings',
    header_star: 'Star this chat',
    header_share: 'Copy chat link',
    header_commands: 'Commands (Ctrl+K)',
    header_toggle_theme: 'Toggle theme',
    header_toggle_lang: 'عربي',

    // Onboarding
    welcome_title: 'Welcome to WIDDX Nexus',
    welcome_sub: 'Terminal AI Workspace — by',
    welcome_by: 'MUHAMMAD MUSLIH',
    ob_intro: 'Introduce yourself',
    ob_code: 'Write code',
    ob_research: 'Research',
    ob_howwiddx: 'How WIDDX works',
    tip_commands: 'Commands',
    tip_slash: 'Slash commands',
    tip_nav: 'Navigation',

    // Input
    input_placeholder: 'Send a message to WIDDX...',
    input_hint: 'Enter to send · Shift+Enter for new line · Ctrl+K for commands',
    disclaimer: 'WIDDX may produce inaccurate information. Verify important outputs.',

    // Status
    status_ready: 'Ready',
    status_processing: 'WIDDX is processing…',
    status_typing: 'Thinking…',

    // Right Panel
    panel_computer: 'WIDDX Computer',
    panel_live: 'Live',
    tab_desktop: 'Desktop',
    tab_terminal: 'Terminal',
    tab_browser: 'Browser',
    tab_files: 'Files',
    panel_loading: 'Loading system info...',
    panel_ready: 'Ready',

    // Command Palette
    cmd_placeholder: 'Type a command or search…',
    cmd_actions: 'Actions',
    cmd_new_chat: 'New Chat',
    cmd_toggle_nav: 'Toggle Navigation',
    cmd_toggle_panel: 'Toggle Computer Panel',
    cmd_toggle_theme: 'Toggle Theme',
    cmd_toggle_lang: 'Switch Language',
    cmd_views: 'Views',
    cmd_view_chat: 'Chat',
    cmd_view_dashboard: 'Dashboard',
    cmd_view_settings: 'Settings',
    cmd_tools: 'Tools',
    cmd_scheduler: 'Task Scheduler',
    cmd_sessions: 'Sessions',
    cmd_memory: 'Memory',
    cmd_skills: 'Skills',
    cmd_gateway: 'Gateway',
    cmd_delegation: 'Delegation',
    cmd_activity: 'Activity',
    cmd_conversation: 'Conversation',
    cmd_clear: 'Clear Conversation',
    cmd_export: 'Export',
    cmd_help: 'Help',
    cmd_shortcuts: 'Keyboard Shortcuts',

    // Toast messages
    toast_copied: 'Copied to clipboard',
    toast_starred: 'Chat starred',
    toast_unstarred: 'Star removed',
    toast_cleared: 'Conversation cleared',
    toast_exported: 'Exported successfully',
    toast_lang_en: 'Switched to English',
    toast_lang_ar: 'تم التبديل إلى العربية',
  },

  ar: {
    // Brand
    brand_name: 'ويدكس نيكسس',
    brand_badge: 'v3',

    // Sidebar
    new_chat: 'محادثة جديدة',
    nav_chat: 'الدردشة',
    nav_dashboard: 'لوحة التحكم',
    nav_settings: 'الإعدادات',
    nav_live: '● مباشر',

    // User
    user_name: 'مستخدم WIDDX',
    user_connected: 'متصل',

    // Chat Header
    header_switch_model: 'تغيير النموذج',
    header_open_settings: 'فتح الإعدادات',
    header_star: 'تمييز المحادثة',
    header_share: 'نسخ رابط المحادثة',
    header_commands: 'الأوامر (Ctrl+K)',
    header_toggle_theme: 'تبديل المظهر',
    header_toggle_lang: 'English',

    // Onboarding
    welcome_title: 'مرحباً بك في ويدكس نيكسس',
    welcome_sub: 'بيئة عمل الذكاء الاصطناعي — بواسطة',
    welcome_by: 'محمد مصلح',
    ob_intro: 'قدّم نفسك',
    ob_code: 'اكتب كوداً',
    ob_research: 'ابحث',
    ob_howwiddx: 'كيف يعمل WIDDX',
    tip_commands: 'الأوامر',
    tip_slash: 'أوامر Slash',
    tip_nav: 'التنقل',

    // Input
    input_placeholder: 'أرسل رسالة إلى WIDDX...',
    input_hint: 'Enter للإرسال · Shift+Enter لسطر جديد · Ctrl+K للأوامر',
    disclaimer: 'قد تنتج WIDDX معلومات غير دقيقة. تحقق من المخرجات المهمة.',

    // Status
    status_ready: 'جاهز',
    status_processing: 'WIDDX يعالج…',
    status_typing: 'يفكر…',

    // Right Panel
    panel_computer: 'WIDDX كمبيوتر',
    panel_live: 'مباشر',
    tab_desktop: 'سطح المكتب',
    tab_terminal: 'الطرفية',
    tab_browser: 'المتصفح',
    tab_files: 'الملفات',
    panel_loading: 'جارٍ تحميل معلومات النظام...',
    panel_ready: 'جاهز',

    // Command Palette
    cmd_placeholder: 'اكتب أمراً أو ابحث…',
    cmd_actions: 'الإجراءات',
    cmd_new_chat: 'محادثة جديدة',
    cmd_toggle_nav: 'إظهار/إخفاء التنقل',
    cmd_toggle_panel: 'تبديل لوحة الكمبيوتر',
    cmd_toggle_theme: 'تبديل المظهر',
    cmd_toggle_lang: 'تبديل اللغة',
    cmd_views: 'العروض',
    cmd_view_chat: 'الدردشة',
    cmd_view_dashboard: 'لوحة التحكم',
    cmd_view_settings: 'الإعدادات',
    cmd_tools: 'الأدوات',
    cmd_scheduler: 'جدولة المهام',
    cmd_sessions: 'الجلسات',
    cmd_memory: 'الذاكرة',
    cmd_skills: 'المهارات',
    cmd_gateway: 'البوابة',
    cmd_delegation: 'التفويض',
    cmd_activity: 'النشاط',
    cmd_conversation: 'المحادثة',
    cmd_clear: 'مسح المحادثة',
    cmd_export: 'تصدير',
    cmd_help: 'المساعدة',
    cmd_shortcuts: 'اختصارات لوحة المفاتيح',

    // Toast messages
    toast_copied: 'تم النسخ إلى الحافظة',
    toast_starred: 'تم تمييز المحادثة',
    toast_unstarred: 'تمت إزالة التمييز',
    toast_cleared: 'تم مسح المحادثة',
    toast_exported: 'تم التصدير بنجاح',
    toast_lang_en: 'Switched to English',
    toast_lang_ar: 'تم التبديل إلى العربية',
  },
};

const Lang = (() => {
  let _lang = localStorage.getItem('widdx_lang') || 'en';

  /** Return translated string for key, or key itself as fallback */
  function t(key) {
    return (_translations[_lang] || {})[key] || (_translations['en'] || {})[key] || key;
  }

  /** Is the current language RTL? */
  function isRTL() {
    return _lang === 'ar';
  }

  /** Apply lang + direction to the <html> element */
  function _applyToDOM() {
    const html = document.documentElement;
    html.setAttribute('lang', _lang);
    html.setAttribute('dir', isRTL() ? 'rtl' : 'ltr');
  }

  /** Translate all elements with [data-i18n] attribute */
  function _translateDOM() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const attr = el.getAttribute('data-i18n-attr'); // e.g. "placeholder" or "title"
      const val = t(key);
      if (attr) {
        el.setAttribute(attr, val);
      } else {
        el.textContent = val;
      }
    });
  }

  /** Switch language and persist */
  function setLang(lang) {
    if (!_translations[lang]) return;
    _lang = lang;
    localStorage.setItem('widdx_lang', lang);
    _applyToDOM();
    _translateDOM();

    // Fire custom event so other modules can react
    document.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
  }

  /** Toggle between English and Arabic */
  function toggle() {
    setLang(_lang === 'en' ? 'ar' : 'en');
    // Show toast
    const key = _lang === 'ar' ? 'toast_lang_ar' : 'toast_lang_en';
    if (typeof showToast === 'function') showToast(t(key), 'info');
  }

  /** Initialize on page load */
  function init() {
    _applyToDOM();
    // Defer DOM translation until content is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', _translateDOM);
    } else {
      _translateDOM();
    }
  }

  return {
    get currentLang() { return _lang; },
    t,
    isRTL,
    setLang,
    toggle,
    init,
  };
})();

// Auto-initialize
Lang.init();

// Expose globally
window.Lang = Lang;
