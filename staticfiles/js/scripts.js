// Theme toggle
function toggleTheme() {
  document.body.classList.toggle("dark-theme");
  const themeToggle = document.querySelector(".theme-toggle");
  if (document.body.classList.contains("dark-theme")) {
    themeToggle.textContent = "☀️";
  } else {
    themeToggle.textContent = "🌙";
  }
}

// Dark theme styles
const darkThemeStyles = document.createElement("style");
darkThemeStyles.innerHTML = 
  body.dark-theme {
    background: #1a1a1a;
    color: #f5f5f5;
  }
  body.dark-theme .navbar {
    background: rgba(20,20,20,0.6);
  }
  body.dark-theme .carousel-item,
  body.dark-theme .plan-box {
    background: #2d2d2d;
  }
  body.dark-theme a,
  body.dark-theme h2,
  body.dark-theme h3 {
    color: #f5f5f5;
  }
  body.dark-theme .btn,
  body.dark-theme .btn-small {
    background: #d46a2f;
    color: #fff;
  }
;
document.head.appendChild(darkThemeStyles);

document.addEventListener("DOMContentLoaded", () => {
  const carousels = document.querySelectorAll('.carousel-container');

  carousels.forEach(carousel => {
    const btnPrev = document.createElement('button');
    btnPrev.className = 'carousel-arrow prev';
    btnPrev.innerHTML = '‹';
    carousel.parentElement.appendChild(btnPrev);

    const btnNext = document.createElement('button');
    btnNext.className = 'carousel-arrow next';
    btnNext.innerHTML = '›';
    carousel.parentElement.appendChild(btnNext);

    const scrollAmount = carousel.offsetWidth * 0.8;

    btnPrev.addEventListener('click', () => {
      carousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
    });

    btnNext.addEventListener('click', () => {
      carousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    });

    // Optional: support arrow keys when focused
    carousel.setAttribute('tabindex', '0');
    carousel.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight') {
        carousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
      } else if (e.key === 'ArrowLeft') {
        carousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
      }
    });
  });
});

function selectSeat(seatId, isBooked) {
    if (isBooked) {
        showPopup();
    } else {
        document.getElementById('seat_id').value = seatId;
    }
}

function showPopup() {
    document.getElementById('popup').style.display = 'flex';
}

function closePopup() {
    document.getElementById('popup').style.display = 'none';
}

// LOGIN PAGE SPECIFIC JS
if(document.body.classList.contains('login-page')) {
    const inputs = document.querySelectorAll("body.login-page input");
    inputs.forEach(input => {
        input.addEventListener("focus", () => {
            input.style.backgroundColor = "#fff";
        });
        input.addEventListener("blur", () => {
            input.style.backgroundColor = "#fff";
        });
    });

    // Theme toggle button
    const themeBtn = document.createElement("button");
    themeBtn.textContent = "🌙";
    themeBtn.style.position = "fixed";
    themeBtn.style.top = "1rem";
    themeBtn.style.right = "1rem";
    themeBtn.style.padding = "0.5rem 1rem";
    themeBtn.style.border = "none";
    themeBtn.style.borderRadius = "8px";
    themeBtn.style.cursor = "pointer";
    themeBtn.style.background = "#d46a2f";
    themeBtn.style.color = "#fff";
    themeBtn.style.fontSize = "1.2rem";
    themeBtn.style.zIndex = "1000";
    document.body.appendChild(themeBtn);

    themeBtn.addEventListener("click", () => {
        document.body.classList.toggle("light-theme");
        themeBtn.textContent = document.body.classList.contains("light-theme") ? "🌙" : "☀️";
    });
}

// Signup page JS - Home Theme
document.addEventListener("DOMContentLoaded", () => {
    const signupPage = document.querySelector('.signup-page');
    if (!signupPage) return;

    const inputs = signupPage.querySelectorAll("input, select");
    inputs.forEach(input => {
        input.addEventListener("focus", () => {
            input.style.backgroundColor = "#fff";
        });
        input.addEventListener("blur", () => {
            input.style.backgroundColor = "#fff";
        });
    });

    // Theme toggle button
    let themeBtn = document.querySelector('.signup-page #theme-toggle-btn');
    if (!themeBtn) {
        themeBtn = document.createElement("button");
        themeBtn.id = "theme-toggle-btn";
        themeBtn.textContent = "🌙";
        themeBtn.style.position = "fixed";
        themeBtn.style.top = "1rem";
        themeBtn.style.right = "1rem";
        themeBtn.style.padding = "0.5rem 1rem";
        themeBtn.style.border = "none";
        themeBtn.style.borderRadius = "8px";
        themeBtn.style.cursor = "pointer";
        themeBtn.style.background = "#d46a2f";
        themeBtn.style.color = "#fff";
        themeBtn.style.fontSize = "1.2rem";
        themeBtn.style.zIndex = "1000";
        document.body.appendChild(themeBtn);
    }

    themeBtn.addEventListener("click", () => {
        signupPage.classList.toggle("light-theme");
        themeBtn.textContent = signupPage.classList.contains("light-theme") ? "🌙" : "☀️";
    });
});


document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('streamingSearch');
  const categoryFilter = document.getElementById('streamingCategory');
  const genreFilter = document.getElementById('streamingGenre');
  const languageFilter = document.getElementById('streamingLanguage');
  const filterBtn = document.getElementById('streamingFilterBtn');

  const cards = Array.from(document.querySelectorAll('.streaming-card'));

  function filterCards() {
    const searchValue = searchInput.value.toLowerCase();
    const categoryValue = categoryFilter.value;
    const genreValue = genreFilter.value;
    const languageValue = languageFilter.value;

    cards.forEach(card => {
      const matchesSearch = card.dataset.title.includes(searchValue);
      const matchesCategory = !categoryValue || card.dataset.category === categoryValue;
      const matchesGenre = !genreValue || card.dataset.genre === genreValue;
      const matchesLanguage = !languageValue || card.dataset.language === languageValue;

      if (matchesSearch && matchesCategory && matchesGenre && matchesLanguage) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });
  }

  filterBtn.addEventListener('click', filterCards);

  // Optional: live search on keyup
  searchInput.addEventListener('keyup', filterCards);
});



/* 🎬 Streaming Page Rating Script */
document.addEventListener("DOMContentLoaded", function () {
    const stars = document.querySelectorAll("#streaming-star-rating .streaming-star");
    const avgRatingEl = document.getElementById("streaming-avg-rating");
    const ratingForm = document.getElementById("streaming-rating-form");

    if (!stars.length || !ratingForm) return;

    stars.forEach(star => {
        star.addEventListener("click", function () {
            const rating = this.dataset.value;

            // highlight clicked stars
            stars.forEach(s => s.classList.remove("active"));
            for (let i = 0; i < rating; i++) {
                stars[i].classList.add("active");
            }

            // AJAX POST to save rating
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const formData = new FormData(ratingForm);
            formData.set("rating", rating);

            fetch(window.location.href, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && avgRatingEl) {
                    avgRatingEl.textContent = Average Rating: ${data.average_rating} ⭐;
                }
            })
            .catch(error => console.error("Rating error:", error));
        });
    });
});


document.addEventListener("DOMContentLoaded", function () {
    const stars = document.querySelectorAll("#streaming-star-rating .streaming-star");
    const ratingForm = document.getElementById("streaming-rating-form");
    if (!stars.length || !ratingForm) return;

    stars.forEach(star => {
        star.addEventListener("click", () => {
            const rating = parseInt(star.dataset.value);
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const formData = new FormData(ratingForm);
            formData.set("rating", rating);

            // Animate stars
            stars.forEach(s => s.classList.remove("selected", "pop"));
            for (let i = 0; i < rating; i++) {
                stars[i].classList.add("selected", "pop");
            }
            stars.forEach(s => s.addEventListener("animationend", () => s.classList.remove("pop"), { once: true }));

            // Send AJAX POST to save rating
            fetch(window.location.href, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: formData
            })
            .then(resp => resp.json())
            .then(data => {
                if (!data.ok) console.error("Rating error:", data.errors);
            })
            .catch(err => console.error("AJAX error:", err));
        });

        // Hover effect
        star.addEventListener("mouseover", () => {
            const hoverValue = parseInt(star.dataset.value);
            stars.forEach(s => s.classList.remove("selected"));
            for (let i = 0; i < hoverValue; i++) {
                stars[i].classList.add("selected");
            }
        });

        star.addEventListener("mouseout", () => {
            stars.forEach(s => s.classList.remove("selected"));
            // Keep selected based on current form value
            const currentRating = parseInt(ratingForm.querySelector("input[name=rating]").value || 0);
            for (let i = 0; i < currentRating; i++) {
                stars[i].classList.add("selected");
            }
        });
    });
});