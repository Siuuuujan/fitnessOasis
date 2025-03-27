// static/js/scripts.js
document.addEventListener('DOMContentLoaded', () => {
    // Auto-hide navigation and footer
    let lastScroll = 0;
    const navbar = document.querySelector('.nav-bar');
    const footer = document.querySelector('footer');
    const scrollThreshold = 100;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > lastScroll && currentScroll > scrollThreshold) {
            navbar.classList.add('hidden');
            footer.classList.add('hidden');
        } else {
            navbar.classList.remove('hidden');
            footer.classList.remove('hidden');
        }
        
        if (currentScroll < 50) {
            navbar.classList.remove('hidden');
            footer.classList.remove('hidden');
        }
        
        lastScroll = currentScroll;
        
        // Parallax effect
        document.getElementById('background-img').style.transform = 
            `translateY(${currentScroll * 0.5}px)`;
    });

    // Slider functionality
    let currentIndex = 0;
    const slides = document.querySelectorAll('.slide');
    const totalSlides = slides.length;

    window.moveSlide = (step) => {
        currentIndex = (currentIndex + step + totalSlides) % totalSlides;
        document.querySelector('.slider-container').style.transform = 
            `translateX(-${currentIndex * 100}%)`;
    }

    setInterval(() => moveSlide(1), 8000);

    // Quick links interaction
    document.querySelectorAll('.three-content div').forEach(link => {
        link.addEventListener('mouseover', () => {
            link.style.transform = 'translateY(-5px)';
        });
        
        link.addEventListener('mouseout', () => {
            link.style.transform = 'translateY(0)';
        });
    });

    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const inputs = form.querySelectorAll('input, textarea');
            let isValid = true;

            inputs.forEach(input => {
                if (!input.checkValidity()) {
                    isValid = false;
                    input.classList.add('invalid');
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Please fill out all required fields correctly.');
            }
        });
    });
});