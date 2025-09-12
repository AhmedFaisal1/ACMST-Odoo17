/** Init hook for phone input; works with or without intl-tel-input. */
odoo.define('acmst_admission.phone', function (require) {
    'use strict';
    const ajax = require('web.ajax');
    function loadScript(src) {
        return new Promise(function(resolve){
            var s = document.createElement('script');
            s.src = src; s.async = true; s.onload = resolve; s.onerror = resolve; document.head.appendChild(s);
        });
    }
    function loadCss(href){
        var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; document.head.appendChild(l);
    }
    async function ensureIntlTelInput() {
        if (window.intlTelInput) return true;
        // Try local assets first
        loadCss('/acmst_admission/static/lib/intl-tel-input/css/intlTelInput.min.css');
        await loadScript('/acmst_admission/static/lib/intl-tel-input/js/intlTelInput.min.js');
        if (window.intlTelInput) return true;
        // Fallback to CDN
        loadCss('https://cdn.jsdelivr.net/npm/intl-tel-input@18.5.6/build/css/intlTelInput.min.css');
        await loadScript('https://cdn.jsdelivr.net/npm/intl-tel-input@18.5.6/build/js/intlTelInput.min.js');
        return !!window.intlTelInput;
    }
    function jsonRpc(url, params){
        return ajax.jsonRpc(url, 'call', params || {});
    }

    const publicRoot = {
        start: async function () {
            const input = document.querySelector('input[name=phone]');
            if (!input) return;
            try {
                const ok = await ensureIntlTelInput();
                if (!ok) return;
                const iti = window.intlTelInput(input, {
                    initialCountry: 'auto',
                    utilsScript: '/acmst_admission/static/lib/intl-tel-input/js/utils.js',
                });
                input.addEventListener('blur', function(){
                    try { if (iti.isValidNumber()) { input.value = iti.getNumber(); } } catch(e){}
                });
            } catch (e) { /* ignore */ }

            // Bind WhatsApp send button (avoid inline onclicks)
            const sendBtn = document.getElementById('btn_send_whatsapp');
            if (sendBtn){
                sendBtn.addEventListener('click', function(){
                    const phone = input.value || '';
                    const key = (sendBtn.dataset && sendBtn.dataset.sitekey) || '';
                    const call = function(token){ jsonRpc('/admissions/otp/send', {phone: phone, recaptcha_token: token}).then(function(r){ alert(r && r.message ? r.message : 'Done'); }); };
                    if (window.grecaptcha && key){ window.grecaptcha.execute(key, {action: 'otp_send'}).then(call); } else { call(null); }
                });
            }

            const verifyBtn = document.getElementById('btn_verify_otp');
            const otpInput = document.getElementById('otp_code');
            if (verifyBtn && otpInput){
                verifyBtn.addEventListener('click', function(){
                    const key = (verifyBtn.dataset && verifyBtn.dataset.sitekey) || '';
                    const code = otpInput.value || '';
                    const call = function(token){ jsonRpc('/admissions/otp/verify', {code: code, recaptcha_token: token}).then(function(r){ if(r && r.ok){ window.location='/admissions/profile'; } else { alert((r && r.message) || 'Failed'); } }); };
                    if (window.grecaptcha && key){ window.grecaptcha.execute(key, {action: 'otp_verify'}).then(call); } else { call(null); }
                });
            }
        }
    };
    document.addEventListener('DOMContentLoaded', function () { publicRoot.start(); });
    return publicRoot;
});
