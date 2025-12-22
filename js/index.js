// js/final-countdown.js
{
    const rows = Array.from(document.querySelectorAll('.board .team-row'));
    const ranksWrapper = document.querySelector('.ranks-wrapper');
    const ranks = Array.from(ranksWrapper.querySelectorAll('.team-rank'));

    // Сортируем команды по очкам (лучший сверху)
    let sortedRows = [...rows].sort((a, b) => {
        const sA = parseInt(a.querySelector('.team-points')?.textContent || '0');
        const sB = parseInt(b.querySelector('.team-points')?.textContent || '0');
        return sB - sA;
    });

    let finalActive = false;
    let pendingIndex = -1;

    // ==============================
    // Скрываем все карточки команд полностью
    // ==============================
    function startFinal() {
        finalActive = true;
        pendingIndex = -1;

        sortedRows.forEach(r => {
            r.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            r.style.opacity = '0';
            r.style.transform = 'translateY(20px)';
        });
    }

    // ==============================
    // Показываем одну команду
    // ==============================
    function revealOne(index) {
        if (index < 0 || index >= sortedRows.length) return;

        const row = sortedRows[index];
        const rankEl = ranks[index];

        row.style.opacity = '1';
        row.style.transform = 'translateY(0) scale(1.05)';
        setTimeout(() => row.style.transform = 'translateY(0) scale(1)', 300);

        if (rankEl) rankEl.textContent = String(index + 1).padStart(2, '0');
    }

    // ==============================
    // Проверка /next через API
    // ==============================
    async function pollFinalTrigger() {
        try {
            const res = await fetch('/api/final');
            const data = await res.json();
            const idx = data.final_index;

            // Старт финала
            if (idx === -2 && !finalActive) {
                startFinal();

                // Первые показываем места с 11 по 4
                for (let i = 10; i >= 3; i--) {
                    setTimeout(() => revealOne(i), (10 - i) * 600);
                }

                // Потом тройка лидеров
                setTimeout(() => revealOne(2), 8 * 600);
                setTimeout(() => revealOne(1), 9 * 600);
                setTimeout(() => revealOne(0), 10 * 600);

            } else if (idx >= 0 && finalActive) {
                if (pendingIndex !== idx) {
                    pendingIndex = idx;
                    revealOne(pendingIndex);
                }
            }
        } catch (e) {
            console.warn("Final countdown poll error:", e);
        }
    }

    setInterval(pollFinalTrigger, 500);
}
