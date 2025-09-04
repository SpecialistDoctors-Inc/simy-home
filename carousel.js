document.addEventListener('DOMContentLoaded', function() {
    const track = document.querySelector('.carousel-simple .carousel-track');
    const avatars = Array.from(track.children);
    const indicators = document.querySelectorAll('.carousel-indicator');
    let currentIndex = 0;


    function updateCarousel(index) {
        avatars.forEach((img, i) => {
            img.style.display = (i === index) ? 'block' : 'none';
        });
        indicators.forEach((btn, i) => {
            btn.classList.toggle('active', i === index);
        });
        currentIndex = index;
    }

    indicators.forEach((btn, i) => {
        btn.addEventListener('click', () => {
            updateCarousel(i);
        });
    });

    // 初期表示
    updateCarousel(0);
});