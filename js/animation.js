// animation.js — Анимация /round для F1 Grand Prix

let isAnimating = false;
let lastTrigger = false;

// Находим элементы
const rows = Array.from(document.querySelectorAll('.team-row'));
const ranks = Array.from(document.querySelectorAll('.ranks-wrapper .team-rank'));

// Инициализируем order
rows.forEach((row, i) => {
    if (row.style.order === '') row.style.order = i;
});

// Переместить команду в новую позицию с анимацией
function moveRowTo(row, targetIndex) {
    const currentOrder = parseInt(row.style.order || 0);
    if (currentOrder === targetIndex) return;

    const currentTop = row.offsetTop;
    row.style.order = targetIndex;
    void row.offsetParent; // reflow
    const newTop = row.offsetTop;

    row.style.transition = 'none';
    row.style.transform = `translateY(${currentTop - newTop}px)`;
    requestAnimationFrame(() => {
        row.style.transition = 'transform 0.5s cubic-bezier(0.2,0,0,1)';
        row.style.transform = 'translateY(0)';
    });
}

// Сортировка по очкам + обновление рангов
function animateToRealRanking() {
    const sorted = [...rows].sort((a, b) => {
        const scoreA = parseInt(a.querySelector('.team-points')?.textContent || '0');
        const scoreB = parseInt(b.querySelector('.team-points')?.textContent || '0');
        return scoreB - scoreA;
    });

    sorted.forEach((row, idx) => {
        moveRowTo(row, idx);
        if (ranks[idx]) {
            ranks[idx].textContent = String(idx + 1).padStart(2, '0');
        }
    });
}

// Имитация "борьбы" — случайные перестановки
function simulateRace() {
    if (isAnimating) return;
    isAnimating = true;

    let step = 0;
    const totalSteps = 5;

    const shuffleStep = () => {
        if (step >= totalSteps) {
            setTimeout(() => {
                animateToRealRanking();
                setTimeout(() => { isAnimating = false; }, 600);
            }, 300);
            return;
        }

        const shuffled = [...rows].sort(() => Math.random() - 0.5);
        shuffled.forEach((row, idx) => moveRowTo(row, idx));

        step++;
        setTimeout(shuffleStep, 400);
    };

    shuffleStep();
}

// Опрос API
async function pollScores() {
    try {
        const res = await fetch('/api/scores');
        if (!res.ok) return;
        const data = await res.json();

        // Обновляем очки
        data.teams.forEach(team => {
            // Ищем по порядку (если нет data-id)
            const row = rows[team.id - 1];
            if (row) {
                const ptsEl = row.querySelector('.team-points');
                if (ptsEl) ptsEl.textContent = team.score;
            }
        });

        // Запуск анимации
        if (data.trigger_round && !lastTrigger) {
            lastTrigger = true;
            simulateRace();
            setTimeout(() => { lastTrigger = false; }, 6000);
        }
    } catch (e) {
        console.warn("Poll error:", e);
    }
}

// Старт
setInterval(pollScores, 1000);
pollScores();

// Для отладки
window.simulateRace = simulateRace;