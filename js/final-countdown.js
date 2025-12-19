// js/final-countdown.js
{
    const ranksWrapper = document.querySelector('.ranks-wrapper');
    const rows = Array.from(document.querySelectorAll('.team-row'));
    const ranks = Array.from(ranksWrapper.querySelectorAll('.team-rank'));

    // Сортируем команды по очкам (лучший сверху)
    let sortedRows = [...rows].sort((a, b) => {
        const sA = parseInt(a.querySelector('.team-points')?.textContent || '0');
        const sB = parseInt(b.querySelector('.team-points')?.textContent || '0');
        return sB - sA;
    });

    let revealedIndex = -1; // уже открытые команды
    let pendingIndex = -1;  // индекс команды, которую надо открыть по следующему /next
    let finalActive = false;

    function startFinal() {
        finalActive = true;
        revealedIndex = -1;
        pendingIndex = -1;

        sortedRows.forEach(r => {
            r.style.opacity = '0';
            r.style.transform = 'translateY(20px)';
            r.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        });
    }

    function revealOne(index) {
        if (index < 0 || index >= sortedRows.length) return;

        const row = sortedRows[index];
        const rankEl = ranks[index];

        row.style.opacity = '1';
        row.style.transform = 'translateY(0) scale(1.1)';
        setTimeout(() => row.style.transform = 'translateY(0) scale(1)', 300);

        if (rankEl) rankEl.textContent = String(index + 1).padStart(2, '0');
        revealedIndex = index;
    }

    async function pollFinalTrigger() {
        try {
            const res = await fetch('/api/final');
            const data = await res.json();
            const idx = data.final_index;

            if (idx === -2 && !finalActive) {
                // старт финала
                startFinal();
            } else if (idx >= 0) {
                // открываем ровно одну команду
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
