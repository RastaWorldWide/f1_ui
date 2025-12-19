{
    let isAnimating = false;
    let lastTrigger = false;

    const board = document.querySelector('.board');
    const rows = Array.from(document.querySelectorAll('.team-row'));
    const ranks = Array.from(document.querySelectorAll('.ranks-wrapper .team-rank'));

    if (!rows.length) return;

    const ROW_HEIGHT = rows[0].offsetHeight;
    const ROW_GAP = 18;

    const ANIMATION = {
        DURATION: 2.5,
        LIFT: 15,
        HOLD: 1.5,
        EASING: 'cubic-bezier(0.4, 0.0, 0.2, 1)'
    };

    function initPositions() {
    board.style.position = 'relative';
    rows.forEach((row, i) => {
        row.style.position = 'absolute';
        row.style.width = '100%';
        row.style.transition = 'none'; // пока без плавного перехода
        row.style.transform = `translateY(${i * (ROW_HEIGHT + ROW_GAP)}px)`;
        row.dataset.pos = i;
    });

    // включаем плавный переход после установки стартовых позиций
    requestAnimationFrame(() => {
        rows.forEach(row => {
            row.style.transition = `transform ${ANIMATION.DURATION}s ${ANIMATION.EASING}`;
        });
    });
}

    function animateSwap(indexA, indexB) {
        return new Promise(resolve => {
            const rowA = rows[indexA];
            const rowB = rows[indexB];

            const posA = Number(rowA.dataset.pos);
            const posB = Number(rowB.dataset.pos);

            const yA = posA * (ROW_HEIGHT + ROW_GAP);
            const yB = posB * (ROW_HEIGHT + ROW_GAP);

            // подсветка обгона
            rowA.classList.add('overtake');
            rowB.classList.add('overtake');

            let transitionsDone = 0;
            function checkDone() {
                transitionsDone++;
                if (transitionsDone === 2) {
                    rowA.dataset.pos = posB;
                    rowB.dataset.pos = posA;
                    rowA.classList.remove('overtake');
                    rowB.classList.remove('overtake');
                    rowA.removeEventListener('transitionend', checkDone);
                    rowB.removeEventListener('transitionend', checkDone);
                    resolve();
                }
            }

            rowA.addEventListener('transitionend', checkDone);
            rowB.addEventListener('transitionend', checkDone);

            rowA.style.transform = `translateY(${yB}px)`;
            rowB.style.transform = `translateY(${yA}px)`;
        });
    }

    function getRankingOrder() {
        return rows
            .map((row, i) => ({
                index: i,
                score: parseInt(row.querySelector('.team-points')?.textContent || '0', 10)
            }))
            .sort((a, b) => b.score - a.score)
            .map(item => item.index);
    }

    async function animateFinalRanking() {
        const finalOrder = getRankingOrder();
        let currentOrder = rows.map((_, i) => i);

        let moved = true;
        while (moved) {
            moved = false;
            // снизу вверх
            for (let i = currentOrder.length - 1; i > 0; i--) {
                const a = currentOrder[i - 1];
                const b = currentOrder[i];

                const scoreA = parseInt(rows[a].querySelector('.team-points')?.textContent || '0', 10);
                const scoreB = parseInt(rows[b].querySelector('.team-points')?.textContent || '0', 10);

                if (scoreA < scoreB) {
                    await animateSwap(a, b);
                    [currentOrder[i - 1], currentOrder[i]] = [b, a];
                    moved = true;
                }
            }
        }

        // обновляем номера мест
        ranks.forEach((rank, i) => {
            rank.textContent = String(i + 1).padStart(2, '0');
        });
    }

//    async function simulateRace() {
//        if (isAnimating) return;
//        isAnimating = true;
//
//        initPositions();
//
//        await sleep(2.0);
//        await animateFinalRanking();
//
//        isAnimating = false;
//    }

    function sleep(seconds) {
        return new Promise(resolve => setTimeout(resolve, seconds * 1000));
    }

    async function pollScores() {
        try {
            const res = await fetch('/api/scores');
            if (!res.ok) return;

            const data = await res.json();
            data.teams.forEach(team => {
                const row = rows[team.id - 1];
                const pts = row?.querySelector('.team-points');
                if (pts) pts.textContent = team.score;
            });

            if (data.trigger_round && !lastTrigger) {
                lastTrigger = true;
                simulateRace();
                setTimeout(() => (lastTrigger = false), 15000);
            }
        } catch (e) {
            console.warn('Poll error:', e);
        }
    }

    setInterval(pollScores, 1000);
    pollScores();

    window.round = simulateRace;
}
