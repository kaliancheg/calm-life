// ========================================
// Navigation Scroll Effect
// ========================================
const nav = document.querySelector('.nav');
const navToggle = document.getElementById('navToggle');
const navMenu = document.querySelector('.nav-menu');

window.addEventListener('scroll', () => {
  if (window.scrollY > 50) {
    nav.classList.add('scrolled');
  } else {
    nav.classList.remove('scrolled');
  }
});

// Mobile Menu Toggle
navToggle.addEventListener('click', () => {
  navMenu.classList.toggle('active');
  navToggle.classList.toggle('active');
});

// Close mobile menu on link click
document.querySelectorAll('.nav-menu a').forEach(link => {
  link.addEventListener('click', () => {
    navMenu.classList.remove('active');
    navToggle.classList.remove('active');
  });
});

// ========================================
// Particles Animation
// ========================================
const particlesContainer = document.getElementById('particles');
const particleCount = 30;

function createParticles() {
  for (let i = 0; i < particleCount; i++) {
    const particle = document.createElement('div');
    particle.classList.add('particle');
    
    // Random position and animation delay
    particle.style.left = `${Math.random() * 100}%`;
    particle.style.animationDelay = `${Math.random() * 20}s`;
    particle.style.animationDuration = `${15 + Math.random() * 15}s`;
    particle.style.width = `${2 + Math.random() * 4}px`;
    particle.style.height = particle.style.width;
    
    particlesContainer.appendChild(particle);
  }
}

createParticles();

// ========================================
// Scroll Animations (Intersection Observer)
// ========================================
const observerOptions = {
  threshold: 0.1,
  rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, observerOptions);

// Add animation classes to elements
document.querySelectorAll('.benefit-card, .practice-card, .testimonial-card, .about-feature, .about-float-card').forEach(el => {
  el.classList.add('fade-in');
  observer.observe(el);
});

document.querySelectorAll('.about-content, .about-visual').forEach(el => {
  el.classList.add('fade-in-left');
  observer.observe(el);
});

document.querySelectorAll('.cta-content, .cta-visual').forEach(el => {
  el.classList.add('fade-in-right');
  observer.observe(el);
});

// ========================================
// Smooth Scroll for Anchor Links
// ========================================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      const offsetTop = target.offsetTop - 80;
      window.scrollTo({
        top: offsetTop,
        behavior: 'smooth'
      });
    }
  });
});

// ========================================
// CTA Form Handler
// ========================================
const ctaForm = document.getElementById('ctaForm');
const ctaEmail = document.getElementById('ctaEmail');
const ctaSuccess = document.getElementById('ctaSuccess');

ctaForm.addEventListener('submit', (e) => {
  e.preventDefault();
  
  const email = ctaEmail.value.trim();
  
  if (email && isValidEmail(email)) {
    // Simulate form submission
    console.log('Email subscribed:', email);
    
    // Show success message
    ctaForm.style.display = 'none';
    ctaSuccess.classList.add('show');
    
    // Reset after 5 seconds
    setTimeout(() => {
      ctaForm.style.display = 'block';
      ctaSuccess.classList.remove('show');
      ctaEmail.value = '';
    }, 5000);
  }
});

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// ========================================
// Counter Animation for Hero Stats
// ========================================
function animateCounter(element, target, suffix = '') {
  let current = 0;
  const increment = target / 50;
  const timer = setInterval(() => {
    current += increment;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    element.textContent = Math.floor(current).toLocaleString() + suffix;
  }, 30);
}

// Observe hero stats
const heroStats = document.querySelector('.hero-stats');
if (heroStats) {
  const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const statNumbers = entry.target.querySelectorAll('.hero-stat-number');
        statNumbers.forEach(stat => {
          const text = stat.textContent;
          if (text.includes('K')) {
            animateCounter(stat, 10, 'K+');
          } else if (text.includes('50')) {
            animateCounter(stat, 50, '+');
          } else if (text.includes('98')) {
            animateCounter(stat, 98, '%');
          }
        });
        statsObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  
  statsObserver.observe(heroStats);
}

// ========================================
// Parallax Effect for Hero Background
// ========================================
const heroBg = document.querySelector('.hero-bg');

window.addEventListener('scroll', () => {
  if (heroBg) {
    const scrolled = window.scrollY;
    heroBg.style.transform = `translateY(${scrolled * 0.3}px)`;
  }
});

// ========================================
// Typing Effect for Hero Subtitle (optional enhancement)
// ========================================
const heroSubtitle = document.querySelector('.hero-subtitle');

if (heroSubtitle) {
  const originalText = heroSubtitle.textContent;
  heroSubtitle.textContent = '';
  
  let charIndex = 0;
  const typeSpeed = 30;
  
  function typeText() {
    if (charIndex < originalText.length) {
      heroSubtitle.textContent += originalText.charAt(charIndex);
      charIndex++;
      setTimeout(typeText, typeSpeed);
    }
  }
  
  // Start typing after a short delay
  setTimeout(typeText, 500);
}

// ========================================
// Active Navigation Link Highlight
// ========================================
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-menu a');

function getPageName(path) {
  const name = path.split('/').pop() || 'index';
  return name.replace(/\.html$/i, '').toLowerCase() || 'index';
}

function getLinkPath(link) {
  const href = link.getAttribute('href') || '';
  if (href.startsWith('#') || href.trim() === '') return 'index';
  return href.split('/').pop().replace(/\.html$/i, '').toLowerCase() || 'index';
}

function updateNavHighlight() {
  const currentPath = getPageName(window.location.pathname);
  let currentSection = '';

  sections.forEach(section => {
    const sectionTop = section.offsetTop;
    if (window.scrollY >= sectionTop - 200) {
      currentSection = section.getAttribute('id');
    }
  });

  navLinks.forEach(link => {
    link.classList.remove('active');
    const href = link.getAttribute('href') || '';
    const linkPath = getLinkPath(link);

    const isCurrentPage = linkPath === currentPath;
    const isCurrentSection = href.startsWith('#') && currentPath === 'index' && href === `#${currentSection}`;

    if (isCurrentPage || isCurrentSection) {
      link.classList.add('active');
    }
  });
}

window.addEventListener('scroll', updateNavHighlight);
window.addEventListener('load', updateNavHighlight);

// ========================================
// Console Welcome Message
// ========================================
console.log('%c🌿 Добро пожаловать в CalmLife!', 'color: #5b8c5a; font-size: 20px; font-weight: bold;');
console.log('%cНайдите свой путь к внутреннему покою.', 'color: #6b6b6b; font-size: 14px;');

// ========================================
// Random Quote Rotator
// ========================================
const quotes = [
  {
    text: 'Вы не можете остановить волны, но вы можете научиться сёрфингу',
    author: 'Джон Кабат-Зинн'
  },
  {
    text: 'Беспокойство не избавляет завтрашний день от его горя — оно лишает сегодняшний день его силы',
    author: 'Корри тен Бом'
  },
  {
    text: 'Тишина — это не отсутствие звука, а состояние души',
    author: 'Лао-цзы'
  },
  {
    text: 'Счастье — это не станция, на которую вы прибываете, а способ путешествия',
    author: 'Маргарет Ли Ранбек'
  },
  {
    text: 'Не в том счастье, чтобы всё было так, как хочешь, а в том, чтобы хотеть то, что есть',
    author: 'Лев Толстой'
  },
  {
    text: 'Внутренний покой начинается в тот момент, когда ты выбираешь не позволять другому человеку или событию контролировать твои эмоции',
    author: 'Пема Чодрон'
  },
  {
    text: 'Жизнь — это 10% того, что с тобой происходит, и 90% того, как ты на это реагируешь',
    author: 'Чарльз Свиндолл'
  },
  {
    text: 'Лучший способ обрести покой — это принять то, что ты не можешь изменить',
    author: 'Эпиктет'
  },
  {
    text: 'Не ищи спокойствия снаружи. Ты не найдёшь его. Ищи внутри, и оно придёт',
    author: 'Руми'
  },
  {
    text: 'Ум — прекрасный слуга, но ужасный хозяин',
    author: 'Робин Шарма'
  },
  {
    text: 'Самое важное — это уметь остановиться. Когда знаешь меру, не бывает опасности',
    author: 'Лао-цзы'
  },
  {
    text: 'Ты не обязан контролировать свои мысли. Ты просто должен перестать позволять им контролировать тебя',
    author: 'Дэн Миллмэн'
  },
  {
    text: 'Медлительность бывает целительной. Замедление позволяет увидеть то, что раньше было скрыто',
    author: 'Тит Нат Хан'
  },
  {
    text: 'Когда вы меняете отношение к жизни, жизнь меняет отношение к вам',
    author: 'Луиза Хей'
  },
  {
    text: 'Покой — это не место, где нет проблем. Это состояние, в котором ты принимаешь их с улыбкой',
    author: 'Шри Чинмой'
  }
];

function setRandomQuote() {
  const quoteText = document.getElementById('quoteText');
  const quoteAuthor = document.getElementById('quoteAuthor');

  if (!quoteText || !quoteAuthor) return;

  const randomIndex = Math.floor(Math.random() * quotes.length);
  const quote = quotes[randomIndex];

  quoteText.textContent = quote.text;
  quoteAuthor.textContent = `— ${quote.author}`;
}

// Set quote on page load
setRandomQuote();
