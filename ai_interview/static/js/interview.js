/**
 * Real-time mock interview: Web Speech API + REST backend
 */
(function () {
    const PHASE_LABELS = {
        introduction: 'Introduction',
        technical: 'Technical',
        behavioral: 'Behavioral',
        closing: 'Closing',
    };

    let session = null;
    let lastAiText = '';
    let recognition = null;
    let isListening = false;
    let timerInterval = null;

    const chatEl = document.getElementById('chat-container');
    const inputEl = document.getElementById('answer-input');
    const timerEl = document.getElementById('timer');
    const progressEl = document.getElementById('progress-bar');
    const phaseEl = document.getElementById('phase-label');
    const roleEl = document.getElementById('interview-role');
    const feedbackEl = document.getElementById('feedback-toast');
    const micErrorEl = document.getElementById('mic-error');

    function init() {
        const raw = sessionStorage.getItem('interview_session');
        if (!raw) {
            window.location.href = '/interview/setup/';
            return;
        }
        session = JSON.parse(raw);
        roleEl.textContent = session.role || 'Mock Interview';
        startTimer(session.time_remaining_seconds || 25 * 60);
        updateProgress(session.progress_percent || 0);

        if (session.current_question) {
            appendAiMessage(session.current_question.text, session.current_question.phase);
        } else {
            pollSession();
        }

        document.getElementById('send-btn').addEventListener('click', submitAnswer);
        document.getElementById('mic-btn').addEventListener('click', toggleMic);
        document.getElementById('speak-btn').addEventListener('click', () => speak(lastAiText));
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitAnswer();
            }
        });

        initSpeechRecognition();
    }

    async function pollSession() {
        const res = await fetch(`/api/interview/session/${session.id}/`);
        if (res.ok) {
            const data = await res.json();
            session = data;
            sessionStorage.setItem('interview_session', JSON.stringify(data));
            if (data.current_question) {
                appendAiMessage(data.current_question.text, data.current_question.phase);
            }
        }
    }

    function startTimer(seconds) {
        let remaining = seconds;
        clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            remaining -= 1;
            if (remaining <= 0) {
                clearInterval(timerInterval);
                timerEl.textContent = '00:00';
                completeInterview();
                return;
            }
            const m = Math.floor(remaining / 60);
            const s = remaining % 60;
            timerEl.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        }, 1000);
        const m = Math.floor(remaining / 60);
        const s = remaining % 60;
        timerEl.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    function updateProgress(pct) {
        progressEl.style.width = `${pct}%`;
    }

    function appendAiMessage(text, phase) {
        lastAiText = text;
        const row = document.createElement('div');
        row.className = 'chat-row';
        row.innerHTML = `
            <div class="flex gap-2">
                <span class="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-xs flex-shrink-0">AI</span>
                <div>
                    <p class="text-xs text-slate-400 mb-1">${PHASE_LABELS[phase] || phase || 'Interviewer'}</p>
                    <div class="chat-bubble-ai">${escapeHtml(text)}</div>
                </div>
            </div>`;
        chatEl.appendChild(row);
        chatEl.scrollTop = chatEl.scrollHeight;
        if (phase) phaseEl.textContent = `Phase: ${PHASE_LABELS[phase] || phase}`;
        speak(text);
    }

    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'chat-row-user';
        row.innerHTML = `<div class="chat-bubble-user">${escapeHtml(text)}</div>`;
        chatEl.appendChild(row);
        chatEl.scrollTop = chatEl.scrollHeight;
    }

    function showFeedback(msg) {
        feedbackEl.textContent = msg;
        feedbackEl.classList.remove('hidden');
        setTimeout(() => feedbackEl.classList.add('hidden'), 4000);
    }

    async function submitAnswer() {
        const answer = inputEl.value.trim();
        if (!answer) return;

        const btn = document.getElementById('send-btn');
        btn.disabled = true;
        appendUserMessage(answer);
        inputEl.value = '';

        try {
            const res = await fetch('/api/interview/answer/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ session_id: session.id, answer }),
            });
            const data = await res.json();

            if (!res.ok) {
                showFeedback(data.error || 'Failed to submit answer.');
                btn.disabled = false;
                return;
            }

            if (data.evaluation?.feedback) {
                showFeedback(`Score: ${data.evaluation.score}% — ${data.evaluation.feedback}`);
            }

            session = data.session;
            sessionStorage.setItem('interview_session', JSON.stringify(session));
            updateProgress(session.progress_percent || 0);

            if (data.is_complete) {
                await completeInterview();
            } else if (data.next_question) {
                setTimeout(() => appendAiMessage(data.next_question.text, data.next_question.phase), 800);
            }
        } catch (_) {
            showFeedback('Network error. Please try again.');
        }
        btn.disabled = false;
    }

    async function completeInterview() {
        const res = await fetch(`/api/interview/complete/${session.id}/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
        });
        if (res.ok) {
            sessionStorage.removeItem('interview_session');
            window.location.href = `/interview/report/${session.id}/`;
        }
    }

    function initSpeechRecognition() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) return;
        recognition = new SR();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (e) => {
            let transcript = '';
            for (let i = e.resultIndex; i < e.results.length; i++) {
                transcript += e.results[i][0].transcript;
            }
            inputEl.value = transcript;
        };

        recognition.onerror = (e) => {
            if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                micErrorEl.classList.remove('hidden');
            }
            stopMic();
        };

        recognition.onend = () => {
            if (isListening) recognition.start();
            else stopMic();
        };
    }

    function toggleMic() {
        if (!recognition) {
            showFeedback('Speech recognition is not supported in this browser. Use Chrome or Edge.');
            return;
        }
        if (isListening) stopMic();
        else startMic();
    }

    function startMic() {
        isListening = true;
        document.getElementById('mic-btn').classList.add('mic-active');
        micErrorEl.classList.add('hidden');
        try {
            recognition.start();
        } catch (_) {}
    }

    function stopMic() {
        isListening = false;
        document.getElementById('mic-btn').classList.remove('mic-active');
        try {
            recognition.stop();
        } catch (_) {}
    }

    function speak(text) {
        if (!text || !window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.rate = 0.95;
        u.pitch = 1;
        const voices = speechSynthesis.getVoices();
        const en = voices.find(v => v.lang.startsWith('en'));
        if (en) u.voice = en;
        speechSynthesis.speak(u);
    }

    if (window.speechSynthesis) {
        speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
    }

    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
