// ヘッダーの表示・非表示をスクロールでヌルヌル制御
let lastScrollY = window.scrollY;
let ticking = false;
const header = document.getElementById('mainHeader');
let isHidden = false;

function onScroll() {
    if (!ticking) {
        window.requestAnimationFrame(() => {
            const currentY = window.scrollY;
            if (currentY > lastScrollY && currentY > 60) {
                // 下にスクロール→隠す
                if (!isHidden) {
                    header.classList.remove('show');
                    header.classList.add('hide');
                    isHidden = true;
                }
            } else {
                // 上にスクロール→表示
                if (isHidden || !header.classList.contains('show')) {
                    header.classList.remove('hide');
                    header.classList.add('show');
                    isHidden = false;
                }
            }
            lastScrollY = currentY;
            ticking = false;
        });
        ticking = true;
    }
}

window.addEventListener('scroll', onScroll);
window.addEventListener('DOMContentLoaded', () => {
    header.classList.add('show');
});
