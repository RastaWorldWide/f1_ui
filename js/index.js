// js/final-countdown.js
document.addEventListener('DOMContentLoaded', () => {
    // ==============================
    // DOM элементы
    // ==============================
    const board = document.querySelector('.board');
    const ranksWrapper = document.querySelector('.ranks-wrapper');
    const ranks = Array.from(ranksWrapper.querySelectorAll('.team-rank'));

    // ==============================
    // Состояние финала
    // ==============================
    let finalActive = false;
    let pendingIndex = -1;
    let sortedRows = [];

    // ==============================
    // Старт финала
    // ==============================
    function startFinal() {
        finalActive = true;
        pendingIndex = -1;

        // 🔹 берём актуальные строки команд на момент старта
        const rows = Array.from(document.querySelectorAll('.board .team-row'));

        // 🔹 сортируем по очкам (лучший сверху)
        sortedRows = [...rows].sort((a, b) => {
            const sA = parseInt(a.querySelector('.team-points')?.textContent || '0', 10);
            const sB = parseInt(b.querySelector('.team-points')?.textContent || '0', 10);
            return sB - sA;
        });

        // 🔹 перестраиваем DOM по рейтингу и скрываем все
        board.innerHTML = '';
        sortedRows.forEach(row => {
            row.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            row.style.opacity = '0';
            row.style.transform = 'translateY(20px)';
            board.appendChild(row);
        });

        console.log('🏁 Финал инициализирован');
    }

    // ==============================
    // Показ одной команды
    // ==============================
    function revealOne(index) {
        if (!finalActive) return;
        if (index < 0 || index >= sortedRows.length) return;

        const row = sortedRows[index];
        const rankEl = ranks[index];

        row.style.opacity = '1';
        row.style.transform = 'translateY(0) scale(1.05)';

        setTimeout(() => {
            row.style.transform = 'translateY(0) scale(1)';
        }, 300);

        if (rankEl) {
            rankEl.textContent = String(index + 1).padStart(2, '0');
        }

        console.log(`➡️ Показано место ${index + 1}`);
    }

    // ==============================
    // Poll /api/final
    // ==============================
    async function pollFinalTrigger() {
        try {
            const res = await fetch('/api/final');
            const data = await res.json();
            const idx = data.final_index;

            // ▶️ Старт финала
            if (idx === -2 && !finalActive) {
                startFinal();
                return;
            }

            // ▶️ Показ команды по /next
            if (finalActive && idx >= 0) {
                if (pendingIndex !== idx) {
                    pendingIndex = idx;
                    revealOne(pendingIndex);
                }
            }
        } catch (e) {
            console.warn('Final countdown poll error:', e);
        }
    }

    // ==============================
    // Запуск polling
    // ==============================
    setInterval(pollFinalTrigger, 500);
});
