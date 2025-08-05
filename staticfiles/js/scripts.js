// Theme
function toggleTheme() {
  const body = document.body;
  const icon = document.getElementById('themeIcon');
  body.classList.toggle('light-mode');
  icon.className = body.classList.contains('light-mode') ? 'fas fa-sun' : 'fas fa-moon';
  localStorage.setItem('theme', body.classList.contains('light-mode') ? 'light' : 'dark');
}

document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem('theme');
  if (saved === 'light') {
    document.body.classList.add('light-mode');
    document.getElementById('themeIcon').className = 'fas fa-sun';
  }
});

// Carousel
let currentSlide = 0;
const track = document.getElementById('carouselTrack');
const totalSlides = track?.children.length ?? 0;

function updateCarousel() {
  if (track) {
    track.style.transform = `translateX(-${currentSlide * 100}%)`;
  }
}

function nextSlide() {
  currentSlide = (currentSlide + 1) % totalSlides;
  updateCarousel();
}

function prevSlide() {
  currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
  updateCarousel();
}

setInterval(nextSlide, 5000); // auto-slide every 5s
